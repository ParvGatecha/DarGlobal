import re
from typing import List, Dict, Any, Optional, Tuple
from backend.app.schemas.agent import IntentType
from backend.app.schemas.chat import ChatMessage
from backend.app.core.logger import logger
from backend.app.agent.conversation_state import (
    conversation_state_manager,
    extract_budget_numeric,
    extract_bedrooms_count,
    extract_property_type_name,
    LOCATION_METADATA,
)

KNOWN_PROJECTS: Dict[str, str] = {
    "pagani": "dg-pagani-geometria",
    "davinci": "dg-pagani-geometria",
    "urban oasis": "dg-urban-oasis",
    "missoni": "dg-urban-oasis",
    "aida": "dg-aida-oman",
    "trump": "dg-aida-oman",
    "w residences": "dg-w-residences-downtown",
    "tierra viva": "dg-tierra-viva-marbella",
    "lamborghini": "dg-tierra-viva-marbella",
    "les vagues": "dg-les-vagues-qatar",
    "elie saab": "dg-les-vagues-qatar",
    "dg1": "dg-dg1-living",
    "tabasheer": "dg-tabasheer-saudi",
    "malqa": "ws-villa-malqa-riyadh",
    "narjis": "ws-duplex-narjis-riyadh",
    "al shati": "ws-seaview-corniche-jeddah",
    "shati": "ws-seaview-corniche-jeddah",
    "al hada": "ws-mansion-hada-riyadh",
    "hada": "ws-mansion-hada-riyadh",
    "wasalt business": "ws-business-riyadh-office",
    "danah": "ws-villa-danah-khobar",
}

SAUDI_LOCATIONS = [
    "riyadh", "jeddah", "al khobar", "khobar",
    "al malqa", "al narjis", "al shati", "al hada", "sedra"
]

DARGLOBAL_LOCATIONS = [
    "dubai", "marbella", "muscat", "qatar", "lusail",
    "tokyo", "japan", "london", "paris", "new york", "singapore", "cairo"
]

RE_TERMS = [
    "property", "properties", "villa", "villas", "apartment", "apartments",
    "duplex", "duplexes", "penthouse", "penthouses", "mansion", "mansions",
    "commercial", "office", "tower", "residence", "residences", "development",
    "developments", "project", "projects", "real estate", "listing", "listings",
    "sqft", "sqm", "handover", "amenity", "amenities", "buy", "sale", "purchase",
    "price", "pricing", "cost", "budget", "sar", "aed", "usd", "riyal", "riyals"
]

GREETING_EXACT = {
    "hi", "hello", "hey", "good morning", "good evening", "good afternoon",
    "good day", "how are you", "how are you doing", "how are you today",
    "whats up", "what's up", "sup", "greetings", "hey there", "hi there",
    "hello there", "howdy", "salaam", "salam", "assalam alaikum", "marhaba"
}

GRATITUDE_EXACT = {
    "thank you", "thanks", "thx", "thank you so much", "thanks a lot",
    "much appreciated", "appreciate it", "that's helpful", "thats helpful",
    "very helpful", "thanks for your help", "thank you for the help"
}

CAPABILITIES_EXACT = {
    "what can you do", "what can you do?", "tell me what you can do",
    "who are you", "who are you?", "what are you", "what are you?",
    "who created you", "how do you work", "what is your purpose",
    "what is darglobal intelligence", "help", "help me",
    "what are your capabilities", "tell me about yourself"
}

GREETING_RESPONSE = (
    "Hello! Welcome to DarGlobal Intelligence.\n\n"
    "I can help you explore DarGlobal developments, discover properties listed on Wasalt, "
    "compare real estate opportunities, and find property information across different locations.\n\n"
    "What would you like to explore today?"
)

GRATITUDE_RESPONSE = (
    "You're very welcome! If you have any further questions about DarGlobal luxury developments "
    "or Wasalt properties in Saudi Arabia, feel free to ask."
)

CAPABILITIES_RESPONSE = (
    "I am **DarGlobal Intelligence**, an executive AI real estate research assistant specializing in:\n\n"
    "- **DarGlobal Luxury Developments**: In-depth information on international flagship projects across Dubai, Muscat, Qatar, and Spain (including branded partnerships with Pagani, Automobili Lamborghini, Missoni, Elie Saab, and Trump International).\n"
    "- **Wasalt Saudi Marketplace**: Real estate listings across Riyadh, Jeddah, and the Eastern Province with verified price ranges, property types, and locations.\n"
    "- **Cross-Market Comparison**: Side-by-side analysis of properties based strictly on verified attributes.\n"
    "- **Data Provenance & Citations**: Verifiable citations and provenance transparency distinguishing live sitemaps from public disclosures.\n\n"
    "What property, development, or location would you like to explore?"
)

UNSUPPORTED_RESPONSE = (
    "I specialize specifically in real estate intelligence for **DarGlobal** luxury developments "
    "and **Wasalt** Saudi Arabian properties.\n\n"
    "I can assist you with property searches, project specifications, location overviews, and comparative analyses "
    "across our verified portfolios. How can I assist you with real estate today?"
)

AMBIGUOUS_BUDGET_RESPONSE = (
    "Which location and currency are you interested in?\n\n"
    "For example:\n"
    "- **Dubai, UAE (AED)**: Ultra-luxury branded developments by DarGlobal (Pagani, Missoni, Gensler, W Residences)\n"
    "- **Riyadh, Saudi Arabia (SAR)**: Residential smart villas, duplexes, and commercial office floors on Wasalt\n"
    "- **Jeddah, Saudi Arabia (SAR)**: Waterfront apartments and corniche residences\n"
    "- **Marbella, Spain (EUR)** or **Muscat, Oman (OMR)**\n\n"
    "Please specify your target city or currency so I can apply the correct budget filter."
)


class IntentClassifier:
    """
    Intent Classifier for DarGlobal Intelligence Agent.
    Categorizes messages into:
    - GREETING
    - GENERAL_CONVERSATION
    - PROPERTY_SEARCH
    - PROJECT_SEARCH
    - PROPERTY_COMPARISON
    - LOCATION_SEARCH
    - PROJECT_DETAILS
    - FOLLOW_UP
    - UNSUPPORTED_QUERY
    """

    @staticmethod
    def extract_budget_sar(text: str) -> Optional[float]:
        t_lower = text.lower()
        sar_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:million|m)\s*(?:sar|riyal|riyals)?", t_lower)
        if not sar_match:
            sar_match = re.search(r"(?:sar|riyal|riyals)\s*(\d+(?:\.\d+)?)\s*(?:million|m)?", t_lower)
        if sar_match:
            try:
                val = float(sar_match.group(1))
                if "million" in t_lower or "m" in t_lower or val < 100:
                    return val * 1_000_000
                return val
            except ValueError:
                pass

        num_direct = re.search(r"under\s*(?:sar)?\s*([\d,]+)", t_lower)
        if num_direct:
            try:
                return float(num_direct.group(1).replace(",", ""))
            except ValueError:
                pass
        return None

    @staticmethod
    def resolve_project_from_history(
        query: str, history: Optional[List[ChatMessage]]
    ) -> Optional[str]:
        if not history:
            return None
        q_lower = query.lower()
        hist_texts = [h.content.lower() for h in history if h.role in ["assistant", "user"]]
        for text in reversed(hist_texts):
            found = [pid for k, pid in KNOWN_PROJECTS.items() if k in text]
            if found:
                ordered = list(dict.fromkeys(found))
                if any(w in q_lower for w in ["first", "first one", "[1]"]):
                    return ordered[0]
                elif any(w in q_lower for w in ["second", "second one", "[2]"]) and len(ordered) > 1:
                    return ordered[1]
                return ordered[0]
        return None

    @classmethod
    def classify(
        cls,
        query: str,
        history: Optional[List[ChatMessage]] = None,
        conversation_id: Optional[str] = None
    ) -> Tuple[IntentType, Dict[str, Any]]:
        clean_q = query.strip()
        q_lower = clean_q.lower()
        q_normalized = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", q_lower).strip()

        # Check for real estate signals
        has_saudi_loc = any(re.search(rf"\b{re.escape(loc)}\b", q_lower) for loc in SAUDI_LOCATIONS)
        has_dg_loc = any(re.search(rf"\b{re.escape(loc)}\b", q_lower) for loc in DARGLOBAL_LOCATIONS)
        has_proj = any(k in q_lower for k in KNOWN_PROJECTS.keys())
        has_wasalt_brand = "wasalt" in q_lower
        has_dg_brand = any(w in q_lower for w in ["darglobal", "dar global", "dar al arkan"])
        has_comparison = any(w in q_lower for w in ["compare", "comparison", "difference", "versus", "vs", "between", "which is better", "contrast"])
        has_re_terms = any(re.search(rf"\b{re.escape(t)}\b", q_lower) for t in RE_TERMS)
        has_budget = cls.extract_budget_sar(query) is not None

        has_real_estate_signal = (
            has_saudi_loc or has_dg_loc or has_proj or has_wasalt_brand or
            has_dg_brand or has_comparison or has_re_terms or has_budget
        )

        # 1. PURE GREETING (Only if no real estate signal is embedded)
        if not has_real_estate_signal:
            if q_normalized in GREETING_EXACT:
                return IntentType.GREETING, {}
            # Match regex greetings like "good morning!", "hey there", "how are you doing"
            if re.match(r"^(hi|hello|hey|good\s+(morning|afternoon|evening|day)|howdy|greetings|salaam|salam|marhaba)(\s+(there|assistant|bot|all))?[\s.!?]*$", q_lower):
                return IntentType.GREETING, {}
            if re.match(r"^(how\s+are\s+you(\s+(doing|today))?|what\'?s\s+up|how\s+is\s+it\s+going)[\s.!?]*$", q_lower):
                return IntentType.GREETING, {}

        # 2. GENERAL CONVERSATION (Gratitude, Capabilities, Identity, Acknowledgments)
        if not has_real_estate_signal:
            if q_normalized in GRATITUDE_EXACT or re.match(r"^(thank\s+you|thanks|thx|thank\s+you\s+so\s+much|thanks\s+a\s+lot|much\s+appreciated|appreciate\s+it|that\'?s\s+helpful|thats\s+helpful|very\s+helpful)[\s.!?]*$", q_lower):
                return IntentType.GENERAL_CONVERSATION, {"sub_type": "gratitude"}

            if q_normalized in CAPABILITIES_EXACT or re.match(r"^(what\s+can\s+you\s+do|tell\s+me\s+what\s+you\s+can\s+do|who\s+are\s+you|what\s+are\s+you|who\s+created\s+you|how\s+do\s+you\s+work|what\s+is\s+your\s+purpose|what\s+is\s+darglobal\s+intelligence|help|help\s+me|what\s+are\s+your\s+capabilities|tell\s+me\s+about\s+yourself)[\s.!?]*$", q_lower):
                return IntentType.GENERAL_CONVERSATION, {"sub_type": "capabilities"}

            if q_normalized in {"ok", "okay", "cool", "great", "awesome", "nice", "got it", "understood"}:
                return IntentType.GENERAL_CONVERSATION, {"sub_type": "acknowledgment"}

            if re.match(r"^(can\s+you\s+explain\s+that|explain|tell\s+me\s+more|can\s+you\s+elaborate)[\s.!?]*$", q_lower):
                return IntentType.GENERAL_CONVERSATION, {"sub_type": "explanation"}

        # 3. CONTEXTUAL FOLLOW-UP CLASSIFICATION & STATE RESOLUTION
        conv_state = conversation_state_manager.get_or_create_state(conversation_id=conversation_id, history=history)
        follow_up_type = conversation_state_manager.classify_follow_up(query, state=conv_state, history=history)

        # A. Ambiguous Follow-up with no prior property context (Test 8)
        if follow_up_type == "AMBIGUOUS_FOLLOW_UP":
            return IntentType.AMBIGUOUS_FOLLOW_UP, {
                "follow_up_type": "AMBIGUOUS_FOLLOW_UP",
                "extracted_budget": extract_budget_numeric(query)
            }

        # B. Budget Refinement on active conversation (Test 1, Test 2)
        if follow_up_type == "BUDGET_REFINEMENT":
            num_budget = extract_budget_numeric(query)
            return IntentType.FOLLOW_UP, {
                "follow_up_type": "BUDGET_REFINEMENT",
                "max_budget": num_budget,
                "location": conv_state.location,
                "currency": conv_state.currency,
                "data_sources": conv_state.data_sources,
                "inherited_property_type": conv_state.property_type,
                "previous_results": conv_state.previous_results
            }

        # C. Bedroom Refinement (Test 3)
        if follow_up_type == "BEDROOM_REFINEMENT":
            bedrooms = extract_bedrooms_count(query)
            return IntentType.FOLLOW_UP, {
                "follow_up_type": "BEDROOM_REFINEMENT",
                "bedrooms": bedrooms,
                "location": conv_state.location,
                "currency": conv_state.currency,
                "data_sources": conv_state.data_sources,
                "inherited_property_type": conv_state.property_type,
                "previous_results": conv_state.previous_results
            }

        # D. Location Refinement (Test 4)
        if follow_up_type == "LOCATION_REFINEMENT":
            loc_match = next((loc for loc in LOCATION_METADATA.keys() if loc in q_lower), None)
            city_name = LOCATION_METADATA[loc_match]["city"] if loc_match else "Riyadh"
            return IntentType.LOCATION_SEARCH, {
                "follow_up_type": "LOCATION_REFINEMENT",
                "location": city_name,
                "inherited_property_type": conv_state.property_type,
                "previous_results": conv_state.previous_results
            }

        # E. Item Details & Referential Follow-up (Test 7)
        is_referential = any(
            re.search(rf"\b{re.escape(p)}\b", q_lower)
            for p in ["its", "it", "this", "that", "these", "those", "first", "second", "third", "[1]", "[2]", "[3]", "former", "latter"]
        )
        is_attribute_query = any(w in q_lower for w in ["amenit", "price", "cost", "handover", "completion", "spec", "where", "location", "developer"])

        if follow_up_type == "DETAILS_FOLLOW_UP" or ((is_referential or is_attribute_query) and history):
            resolved_proj = None
            if conv_state and conv_state.previous_results:
                if any(w in q_lower for w in ["first", "first one", "[1]"]) and len(conv_state.previous_results) >= 1:
                    resolved_proj = conv_state.previous_results[0].get("id")
                elif any(w in q_lower for w in ["second", "second one", "[2]"]) and len(conv_state.previous_results) >= 2:
                    resolved_proj = conv_state.previous_results[1].get("id")
                elif any(w in q_lower for w in ["third", "third one", "[3]"]) and len(conv_state.previous_results) >= 3:
                    resolved_proj = conv_state.previous_results[2].get("id")

            if not resolved_proj:
                resolved_proj = cls.resolve_project_from_history(query, history)

            if resolved_proj:
                if has_comparison:
                    return IntentType.PROPERTY_COMPARISON, {"resolved_project_id": resolved_proj, "from_history": True}
                return IntentType.FOLLOW_UP, {
                    "follow_up_type": "DETAILS_FOLLOW_UP",
                    "resolved_project_id": resolved_proj,
                    "from_history": True,
                    "previous_results": conv_state.previous_results
                }

        # 4. PROPERTY COMPARISON
        if has_comparison:
            matched_pids = [pid for k, pid in KNOWN_PROJECTS.items() if k in q_lower]
            unique_pids = list(dict.fromkeys(matched_pids))
            return IntentType.PROPERTY_COMPARISON, {
                "property_ids": unique_pids,
                "is_cross_market": ("darglobal" in q_lower or "dubai" in q_lower) and ("wasalt" in q_lower or "riyadh" in q_lower)
            }

        # 5. PROJECT DETAILS (Direct project mention)
        matched_pids = [pid for k, pid in KNOWN_PROJECTS.items() if k in q_lower]
        unique_pids = list(dict.fromkeys(matched_pids))
        if len(unique_pids) == 1:
            return IntentType.PROJECT_DETAILS, {"project_id": unique_pids[0]}

        # 6. PROPERTY SEARCH (Wasalt / Saudi Arabia / SAR budget / residential keywords)
        if has_wasalt_brand or (has_saudi_loc and not has_dg_brand):
            city = next((loc.title() for loc in SAUDI_LOCATIONS if loc in q_lower), None)
            ptype = "villa" if "villa" in q_lower else ("apartment" if "apartment" in q_lower else ("duplex" if "duplex" in q_lower else None))
            budget = cls.extract_budget_sar(query)
            return IntentType.PROPERTY_SEARCH, {
                "city": city,
                "property_type": ptype,
                "max_budget_sar": budget
            }

        # 7. PROJECT SEARCH (DarGlobal / International portfolio)
        if has_dg_brand or (has_dg_loc and not has_wasalt_brand):
            city = next((loc.title() for loc in DARGLOBAL_LOCATIONS if loc in q_lower), None)
            return IntentType.PROJECT_SEARCH, {
                "city": city,
                "query": query
            }

        # 8. LOCATION SEARCH (Broad location inquiry without developer)
        if has_saudi_loc or has_dg_loc:
            loc = next((l for l in (SAUDI_LOCATIONS + DARGLOBAL_LOCATIONS) if l in q_lower), None)
            return IntentType.LOCATION_SEARCH, {"location": loc}

        # If general real estate terms are present but no specific location or project
        if has_re_terms or has_budget:
            # Fall back to general property search across platforms
            return IntentType.PROPERTY_SEARCH, {"query": query}

        # 9. UNSUPPORTED QUERY
        return IntentType.UNSUPPORTED_QUERY, {}

    @classmethod
    def get_natural_response(cls, intent: IntentType, query: str = "") -> str:
        q_lower = query.lower()
        if intent == IntentType.GREETING:
            return GREETING_RESPONSE
        elif intent == IntentType.GENERAL_CONVERSATION:
            if any(w in q_lower for w in ["thank", "thanks", "helpful", "appreciat"]):
                return GRATITUDE_RESPONSE
            elif any(w in q_lower for w in ["what can you do", "who are you", "what are you", "help", "capabilities"]):
                return CAPABILITIES_RESPONSE
            elif any(w in q_lower for w in ["ok", "okay", "cool", "great", "nice", "got it", "understood"]):
                return "Understood! Let me know if you would like to explore any properties, developments, or market comparisons."
            return (
                "I am here to assist your real estate research across DarGlobal and Wasalt portfolios. "
                "Feel free to ask about luxury projects in Dubai, Spain, or Oman, or residential properties across Saudi Arabia."
            )
        elif intent == IntentType.AMBIGUOUS_FOLLOW_UP:
            return AMBIGUOUS_BUDGET_RESPONSE
        elif intent == IntentType.UNSUPPORTED_QUERY:
            return UNSUPPORTED_RESPONSE
        return ""
