"""
Structured Conversation State & Contextual Slot Inheritance Manager for DarGlobal Intelligence.

Maintains multi-turn conversation memory, tracks search filters, inherits context across short follow-ups,
and prevents currency/source mismatch or context contamination.
"""

import re
from typing import List, Optional, Dict, Any, Tuple, Literal
from pydantic import BaseModel, Field
from backend.app.schemas.chat import ChatMessage
from backend.app.ingestion.seed_data import SEED_PROJECTS, is_allowed_property_result
from backend.app.core.logger import logger

FollowUpType = Literal[
    "NEW_QUERY",
    "BUDGET_REFINEMENT",
    "LOCATION_REFINEMENT",
    "PROPERTY_TYPE_REFINEMENT",
    "BEDROOM_REFINEMENT",
    "COMPARISON_REQUEST",
    "DETAILS_FOLLOW_UP",
    "GENERAL_FOLLOW_UP",
    "AMBIGUOUS_FOLLOW_UP"
]

LOCATION_METADATA: Dict[str, Dict[str, str]] = {
    # Dubai / UAE
    "dubai": {"country": "United Arab Emirates", "currency": "AED", "default_source": "DarGlobal", "city": "Dubai"},
    "downtown dubai": {"country": "United Arab Emirates", "currency": "AED", "default_source": "DarGlobal", "city": "Dubai"},
    "business bay": {"country": "United Arab Emirates", "currency": "AED", "default_source": "DarGlobal", "city": "Dubai"},
    "uae": {"country": "United Arab Emirates", "currency": "AED", "default_source": "DarGlobal", "city": "Dubai"},

    # Saudi Arabia
    "riyadh": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Riyadh"},
    "north riyadh": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Riyadh"},
    "al malqa": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Riyadh"},
    "al narjis": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Riyadh"},
    "al hada": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Riyadh"},
    "olaya": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Riyadh"},
    "sedra": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "DarGlobal", "city": "Riyadh"},
    "jeddah": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Jeddah"},
    "al shati": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Jeddah"},
    "corniche": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Jeddah"},
    "al khobar": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Al Khobar"},
    "khobar": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Al Khobar"},
    "danah": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Al Khobar"},
    "saudi arabia": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Riyadh"},
    "saudi": {"country": "Saudi Arabia", "currency": "SAR", "default_source": "Wasalt", "city": "Riyadh"},

    # Oman
    "muscat": {"country": "Oman", "currency": "OMR", "default_source": "DarGlobal", "city": "Muscat"},
    "oman": {"country": "Oman", "currency": "OMR", "default_source": "DarGlobal", "city": "Muscat"},
    "yiti": {"country": "Oman", "currency": "OMR", "default_source": "DarGlobal", "city": "Muscat"},

    # Spain
    "marbella": {"country": "Spain", "currency": "EUR", "default_source": "DarGlobal", "city": "Marbella"},
    "benahavís": {"country": "Spain", "currency": "EUR", "default_source": "DarGlobal", "city": "Marbella"},
    "benahavis": {"country": "Spain", "currency": "EUR", "default_source": "DarGlobal", "city": "Marbella"},
    "spain": {"country": "Spain", "currency": "EUR", "default_source": "DarGlobal", "city": "Marbella"},

    # Qatar
    "doha": {"country": "Qatar", "currency": "QAR", "default_source": "DarGlobal", "city": "Doha"},
    "lusail": {"country": "Qatar", "currency": "QAR", "default_source": "DarGlobal", "city": "Lusail"},
    "qetaifan": {"country": "Qatar", "currency": "QAR", "default_source": "DarGlobal", "city": "Lusail"},
    "qatar": {"country": "Qatar", "currency": "QAR", "default_source": "DarGlobal", "city": "Doha"},

    # United Kingdom
    "london": {"country": "United Kingdom", "currency": "GBP", "default_source": "DarGlobal", "city": "London"},
    "uk": {"country": "United Kingdom", "currency": "GBP", "default_source": "DarGlobal", "city": "London"},
}


class ConversationState(BaseModel):
    """
    Structured persistent state for a multi-turn conversation session.
    """
    conversation_id: Optional[str] = None
    intent: Optional[str] = "PROPERTY_SEARCH"
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    data_sources: List[str] = Field(default_factory=list)
    previous_results: List[Dict[str, Any]] = Field(default_factory=list)
    last_search_query: Optional[str] = None
    follow_up_type: Optional[str] = None
    turn_count: int = 0

    def get_active_filters_summary(self) -> Dict[str, Any]:
        """Returns clean dictionary of active applied filters."""
        summary = {}
        if self.location:
            summary["location"] = self.location
        if self.country:
            summary["country"] = self.country
        if self.currency:
            summary["currency"] = self.currency
        if self.budget_max:
            summary["budget_max"] = self.budget_max
            summary["budget_formatted"] = f"Up to {self.currency or ''} {self.budget_max:,.0f}".strip()
        if self.budget_min:
            summary["budget_min"] = self.budget_min
        if self.property_type:
            summary["property_type"] = self.property_type
        if self.bedrooms:
            summary["bedrooms"] = f"{self.bedrooms} Bedrooms"
        if self.data_sources:
            summary["data_sources"] = self.data_sources
            summary["source"] = " & ".join(self.data_sources)
        return summary


def parse_numeric_price(price_str: Optional[str]) -> Optional[float]:
    """Extracts numeric price value from formatted currency string."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.]", "", price_str.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_budget_numeric(text: str) -> Optional[float]:
    """
    Extracts numeric maximum budget from user expressions:
    e.g. 'under 2000000', 'under 2 million', 'under 2m', 'below 3.5m', 'max 3000000'.
    """
    t_lower = text.lower().strip()

    # Pattern 1: 'under 2 million' or 'under 2.5m' or 'under 2m'
    m_million = re.search(r"(?:under|below|max|up to|budget|less than)?\s*(\d+(?:\.\d+)?)\s*(?:million|m)\b", t_lower)
    if m_million:
        try:
            val = float(m_million.group(1))
            return val * 1_000_000
        except ValueError:
            pass

    # Pattern 2: 'under 2000000' or 'under 2,000,000' or '2000000'
    m_num = re.search(r"(?:under|below|max|up to|budget|less than)\s*(?:sar|aed|eur|usd|qar|omr|gbp)?\s*([\d,]+)", t_lower)
    if m_num:
        try:
            val_str = m_num.group(1).replace(",", "")
            val = float(val_str)
            if val < 100:  # e.g. "under 2" interpreted in millions in real estate
                return val * 1_000_000
            return val
        except ValueError:
            pass

    # Pattern 3: Standalone number like '2000000' or '2,000,000'
    m_standalone = re.search(r"^\s*([\d,]+)\s*$", t_lower)
    if m_standalone:
        try:
            val = float(m_standalone.group(1).replace(",", ""))
            if val >= 50_000:
                return val
        except ValueError:
            pass

    return None


def extract_bedrooms_count(text: str) -> Optional[int]:
    """Extracts bedroom count (e.g. 'two bedrooms' -> 2, '3 br' -> 3, '4 bed' -> 4)."""
    t_lower = text.lower()
    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7
    }

    # Match 'two bedrooms', '2 bedrooms', '2 bedroom', '2 br', '2 beds'
    m = re.search(r"\b(one|two|three|four|five|six|seven|\d+)\s*(?:bedroom|bedrooms|br|bed|beds)\b", t_lower)
    if m:
        key = m.group(1)
        if key in word_to_num:
            return word_to_num[key]
        try:
            return int(key)
        except ValueError:
            pass

    if "studio" in t_lower:
        return 0

    return None


def extract_property_type_name(text: str) -> Optional[str]:
    """Extracts property type keyword (villa, apartment, duplex, penthouse, mansion, commercial)."""
    t_lower = text.lower()
    if "villa" in t_lower:
        return "villa"
    if "apartment" in t_lower or "flat" in t_lower:
        return "apartment"
    if "duplex" in t_lower:
        return "duplex"
    if "penthouse" in t_lower:
        return "penthouse"
    if "mansion" in t_lower:
        return "mansion"
    if "office" in t_lower or "commercial" in t_lower:
        return "commercial"
    return None


class ConversationStateManager:
    """
    Session & Conversation Memory Manager for DarGlobal Intelligence.
    Maintains structured state across multiple conversation turns.
    """

    def __init__(self):
        self._cache: Dict[str, ConversationState] = {}

    def get_or_create_state(
        self,
        conversation_id: Optional[str] = None,
        history: Optional[List[ChatMessage]] = None
    ) -> ConversationState:
        """Retrieves existing cached state or reconstructs state from conversation history."""
        cid = conversation_id or "default_session"

        if cid in self._cache and len(self._cache[cid].previous_results) > 0:
            return self._cache[cid]

        # Reconstruct from conversation history if cache is fresh or unpopulated
        if history and len(history) > 0:
            reconstructed = self.reconstruct_state_from_history(history, conversation_id=cid)
            self._cache[cid] = reconstructed
            return reconstructed

        # Default empty state
        state = ConversationState(conversation_id=cid)
        self._cache[cid] = state
        return state

    def save_state(self, state: ConversationState) -> None:
        """Persists conversation state in session cache."""
        cid = state.conversation_id or "default_session"
        self._cache[cid] = state

    def classify_follow_up(
        self,
        query: str,
        state: Optional[ConversationState],
        history: Optional[List[ChatMessage]] = None
    ) -> FollowUpType:
        """
        Classifies incoming message in the context of ongoing conversation history into:
        - NEW_QUERY
        - BUDGET_REFINEMENT
        - LOCATION_REFINEMENT
        - PROPERTY_TYPE_REFINEMENT
        - BEDROOM_REFINEMENT
        - COMPARISON_REQUEST
        - DETAILS_FOLLOW_UP
        - AMBIGUOUS_FOLLOW_UP
        - GENERAL_FOLLOW_UP
        """
        q_clean = query.strip()
        q_lower = q_clean.lower()
        has_prior_context = (state and state.location is not None) or (history and len(history) > 0)

        # 1. Check for explicit overrides ("Actually, show me Dubai apartments", "Instead", "No, show me")
        if re.search(r"\b(actually|instead|scratch that|forget that|no\b)\b", q_lower) and any(
            loc in q_lower for loc in LOCATION_METADATA.keys()
        ):
            return "NEW_QUERY"

        # 2. Check for comparison requests ("Compare properties in Dubai and Riyadh", "Compare the first two")
        if any(w in q_lower for w in ["compare", "comparison", "difference", "versus", "vs", "between"]):
            return "COMPARISON_REQUEST"

        # 3. Check for specific item references ("Show me the second one", "first property", "tell me about [1]")
        if any(
            re.search(rf"\b{re.escape(w)}\b", q_lower)
            for w in ["first", "second", "third", "fourth", "former", "latter", "the first one", "the second one", "second one", "first one", "[1]", "[2]", "[3]"]
        ) or (has_prior_context and any(w in q_lower for w in ["amenities", "amenity", "features", "floor plan", "handover", "details"]) and len(q_lower.split()) < 8):
            return "DETAILS_FOLLOW_UP"

        # 4. Check for Budget Refinement (e.g. "Under 2000000", "Under 2 million", "Max 3m")
        budget_val = extract_budget_numeric(query)
        if budget_val is not None:
            # Check if this message ONLY specifies budget (e.g. "under 2000000", "under 2 million")
            is_budget_only = len(q_lower.split()) <= 4 and not any(loc in q_lower for loc in LOCATION_METADATA.keys())
            if is_budget_only or not any(loc in q_lower for loc in ["dubai", "riyadh", "jeddah", "marbella", "muscat"]):
                if has_prior_context and state and state.location:
                    return "BUDGET_REFINEMENT"
                else:
                    # User says "Under 2 million." with NO previous property-search context (Test 8)
                    return "AMBIGUOUS_FOLLOW_UP"

        # 5. Check for Bedroom Refinement (e.g. "Two bedrooms", "3 br", "4 bed")
        bedrooms = extract_bedrooms_count(query)
        if bedrooms is not None and len(q_lower.split()) <= 4 and not any(loc in q_lower for loc in LOCATION_METADATA.keys()):
            if has_prior_context:
                return "BEDROOM_REFINEMENT"

        # 6. Check for Location Refinement (e.g. "What about Riyadh?", "And Jeddah?", "How about Dubai?")
        loc_match = next((loc for loc in LOCATION_METADATA.keys() if loc in q_lower), None)
        if loc_match and has_prior_context:
            is_followup_pattern = bool(re.search(r"\b(what about|how about|and\b|what of)\s+" + re.escape(loc_match), q_lower))
            is_short_loc = len(q_lower.split()) <= 3 and not any(w in q_lower for w in ["find", "show", "search", "villa", "apartment", "project", "property", "darglobal", "wasalt"])
            if is_followup_pattern or is_short_loc:
                return "LOCATION_REFINEMENT"

        # 7. Check for Property Type Refinement (e.g. "Only villas", "Show me apartments", "Any penthouses?")
        prop_type = extract_property_type_name(query)
        if prop_type and len(q_lower.split()) <= 4 and not any(loc in q_lower for loc in LOCATION_METADATA.keys()):
            if has_prior_context:
                return "PROPERTY_TYPE_REFINEMENT"

        # 8. Check for greetings or capability questions
        if q_lower in ["hi", "hello", "hey"] or any(q_lower.startswith(w) for w in ["good morning", "good evening"]):
            return "NEW_QUERY"

        # Default: if full independent real estate search with location specified
        if loc_match:
            return "NEW_QUERY"

        return "GENERAL_FOLLOW_UP"

    def reconstruct_state_from_history(
        self,
        history: List[ChatMessage],
        conversation_id: Optional[str] = "default_session"
    ) -> ConversationState:
        """
        Reconstructs structured ConversationState by analyzing previous turns in the history.
        Identifies active location, currency, property type, source, and referenced properties.
        """
        state = ConversationState(conversation_id=conversation_id)

        for msg in history:
            content_lower = msg.content.lower()

            # 1. Detect location mentions in user messages
            if msg.role == "user":
                state.last_search_query = msg.content
                for loc_key, meta in LOCATION_METADATA.items():
                    if re.search(rf"\b{re.escape(loc_key)}\b", content_lower):
                        state.location = meta["city"]
                        state.city = meta["city"]
                        state.country = meta["country"]
                        state.currency = meta["currency"]
                        if meta["default_source"] not in state.data_sources:
                            state.data_sources = [meta["default_source"]]
                        break

                # Detect property type
                ptype = extract_property_type_name(msg.content)
                if ptype:
                    state.property_type = ptype

                # Detect bedrooms
                br = extract_bedrooms_count(msg.content)
                if br is not None:
                    state.bedrooms = br

                # Detect budget
                budget = extract_budget_numeric(msg.content)
                if budget is not None:
                    state.budget_max = budget

            # 2. Extract properties returned in assistant messages
            if msg.role == "assistant":
                # Look for project matches from SEED_PROJECTS
                found_in_msg = []
                for p in SEED_PROJECTS:
                    if not is_allowed_property_result(p):
                        continue
                    # Match title or ID in assistant content
                    p_title_short = p["title"].split("(")[0].strip().lower()
                    if p["title"].lower() in content_lower or p_title_short in content_lower:
                        if p not in found_in_msg:
                            found_in_msg.append(p)

                if found_in_msg:
                    state.previous_results = found_in_msg
                    # Inherit location and source if not yet set
                    first_p = found_in_msg[0]
                    if not state.location:
                        state.location = first_p.get("city") or first_p.get("location")
                        state.currency = first_p.get("currency")
                        state.country = first_p.get("country")
                    if not state.data_sources:
                        state.data_sources = [first_p.get("source")]

        return state

    def filter_cached_results_by_budget(
        self,
        results: List[Dict[str, Any]],
        max_budget: float,
        currency: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filters existing cached property results by maximum budget without re-fetching.
        """
        filtered = []
        for prop in results:
            if not is_allowed_property_result(prop):
                continue

            num_price = parse_numeric_price(prop.get("price"))
            if num_price is not None:
                if num_price <= max_budget:
                    filtered.append(prop)
            else:
                # If price is unparsed or POA, keep cautiously
                filtered.append(prop)

        return filtered

    def filter_cached_results_by_bedrooms(
        self,
        results: List[Dict[str, Any]],
        bedrooms: int
    ) -> List[Dict[str, Any]]:
        """
        Filters existing cached property results by bedroom requirement.
        """
        filtered = []
        target_str = str(bedrooms)

        for prop in results:
            meta = prop.get("metadata", {})
            unit_types = str(meta.get("unit_types", "")).lower()
            prop_br = meta.get("bedrooms")
            desc = prop.get("description", "").lower()
            amenities = " ".join(prop.get("amenities", [])).lower()

            # Check direct bedroom field
            if prop_br is not None and prop_br == bedrooms:
                filtered.append(prop)
                continue

            # Check unit_types string (e.g. "2, 3, 4-bedroom apartments")
            if target_str in unit_types or f"{target_str}-bedroom" in desc or f"{target_str} bedroom" in desc or f"{target_str} br" in amenities:
                filtered.append(prop)
                continue

        # If strict filter returned nothing, return all to prevent false empty
        return filtered if filtered else results


# Singleton instance
conversation_state_manager = ConversationStateManager()
