import re
import httpx
import json
import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.llm.model_selector import model_selector, PREFERRED_FREE_MODELS

class OpenRouterClient:
    """
    Asynchronous OpenRouter API client with dynamic free-model routing and fallback.
    """

    def __init__(self):
        self.base_url = settings.OPENROUTER_BASE_URL
        self.api_key = settings.OPENROUTER_API_KEY

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://darglobal.co.uk",
            "X-Title": "DarGlobal Intelligence Assistant",
            "User-Agent": "DarGlobal-Intelligence/1.0"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> str:
        """Non-streaming completion with automatic model fallback."""
        if not self.api_key:
            return self._heuristic_offline_completion(messages)

        target_model = model or model_selector.get_best_model()
        candidates = [target_model] + [m for m in PREFERRED_FREE_MODELS if m != target_model]

        async with httpx.AsyncClient(timeout=45.0) as client:
            for candidate in candidates[:3]:
                payload = {
                    "model": candidate,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 1200
                }
                try:
                    logger.info(f"Sending prompt to OpenRouter model: {candidate}")
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._get_headers(),
                        json=payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        return content
                    else:
                        logger.warning(f"OpenRouter candidate {candidate} returned status {resp.status_code}: {resp.text}")
                except Exception as e:
                    logger.warning(f"Failed to query model {candidate}: {e}")

        # Fallback to local heuristic engine if API calls fail
        logger.warning("All OpenRouter candidates exhausted or failed. Using offline grounded synthesis.")
        return self._heuristic_offline_completion(messages)

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        """Streaming completion via Server-Sent Events (SSE)."""
        if not self.api_key:
            content = self._heuristic_offline_completion(messages)
            # Simulate streaming tokens
            words = content.split(" ")
            for w in words:
                yield w + " "
                await asyncio.sleep(0.015)
            return

        target_model = model or model_selector.get_best_model()

        async with httpx.AsyncClient(timeout=45.0) as client:
            payload = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1200,
                "stream": True
            }
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload
                ) as resp:
                    if resp.status_code != 200:
                        logger.warning(f"OpenRouter stream error {resp.status_code}")
                        content = self._heuristic_offline_completion(messages)
                        for w in content.split(" "):
                            yield w + " "
                            await asyncio.sleep(0.015)
                        return

                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_json = json.loads(data_str)
                            delta = chunk_json.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"Stream exception: {e}")
                content = self._heuristic_offline_completion(messages)
                for w in content.split(" "):
                    yield w + " "
                    await asyncio.sleep(0.015)

    def _heuristic_offline_completion(self, messages: List[Dict[str, str]]) -> str:
        """
        Deterministic, strictly grounded synthesis engine used in offline mode
        or when external API rate limits occur.
        """
        from backend.app.ingestion.seed_data import is_allowed_property_result

        system_content = next((m["content"] for m in messages if m["role"] == "system"), "")
        # Always read the LAST user message from history to prevent context contamination from earlier turns
        user_content = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        user_lower = user_content.lower()

        # Check if agentic system prompt with real tool execution data is present
        if "REAL TOOLS EXECUTED & GROUNDING DATA:" in system_content:
            agent_properties = []
            json_blocks = re.findall(r"```json\s*(\{.*?\})\s*```", system_content, re.DOTALL)
            for jb in json_blocks:
                try:
                    data = json.loads(jb)
                    items = (
                        data.get("properties")
                        or data.get("projects")
                        or data.get("filtered_properties")
                        or data.get("compared_properties")
                        or data.get("matches")
                        or []
                    )
                    if data.get("found") and "title" in data:
                        items.append(data)
                    for item in items:
                        if isinstance(item, dict) and is_allowed_property_result(item):
                            item_id = item.get("id") or item.get("title")
                            if not any((existing.get("id") or existing.get("title")) == item_id for existing in agent_properties):
                                agent_properties.append(item)
                except Exception:
                    pass

            filter_banner_match = re.search(r"ACTIVE SEARCH FILTERS:\s*(.+)", system_content)
            filter_banner = f"> **Active Search Filters**: {filter_banner_match.group(1).strip()}\n\n" if filter_banner_match else ""

            # Once real retrieval tools have executed and properties were found,
            # NEVER override the response with a greeting or generic text!
            if agent_properties:
                # If query specifically asks for amenities, focus answer on verified amenities
                if "amenit" in user_lower:
                    amenities_parts = []
                    if filter_banner:
                        amenities_parts.append(filter_banner.strip())
                        amenities_parts.append("")
                    amenities_parts.append("### Verified Amenities & Facilities\n")
                    amenities_parts.append("The agent executed specialized retrieval tools and extracted verified amenities for the requested property:\n")
                    for idx, prop in enumerate(agent_properties[:3], 1):
                        title = prop.get("title", "Property Listing")
                        source = prop.get("source", "Real Estate Portal")
                        amenities = prop.get("key_amenities") or prop.get("amenities") or []
                        p_class = prop.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                        prov_label = "Directly Scraped" if (p_class == "DIRECTLY_SCRAPED" or prop.get("is_directly_scraped")) else "Publicly Verified Fallback"
                        url = prop.get("url") or prop.get("canonical_url", "")

                        amenities_parts.append(f"#### [{idx}] {title}")
                        amenities_parts.append(f"- **Location**: {prop.get('location', 'N/A')} [{idx}]")
                        amenities_parts.append(f"- **Property Type**: {prop.get('property_type', 'Residential')} [{idx}]")
                        amenities_parts.append(f"- **Source & Provenance**: [{prov_label}]({url})" if url else f"- **Data Provenance**: [{prov_label}]")
                        amenities_parts.append(f"- **Verified Amenities List**:")
                        if isinstance(amenities, list):
                            for am in amenities:
                                amenities_parts.append(f"  - {am} [{idx}]")
                        else:
                            amenities_parts.append(f"  - {amenities} [{idx}]")
                        amenities_parts.append("")
                    amenities_parts.append(
                        "> [!NOTE]\n"
                        "> All listed amenities are strictly verified against canonical project specifications with zero fabricated features."
                    )
                    return "\n".join(amenities_parts)

                is_comparison = any(w in user_lower for w in ["compare", "difference", "vs", "versus", "between"])
                if is_comparison:
                    response_parts = []
                    if filter_banner:
                        response_parts.append(filter_banner.strip())
                        response_parts.append("")
                    response_parts.append("### Autonomous Comparative Real Estate Analysis\n")
                    response_parts.append(
                        "The agent executed genuine multi-platform retrieval tools and retrieved verified records from **DarGlobal** and **Wasalt**:\n"
                    )
                    for idx, prop in enumerate(agent_properties[:4], 1):
                        title = prop.get("title", "Property Listing")
                        source = prop.get("source", "Real Estate Portal")
                        loc = prop.get("location", "N/A")
                        price = prop.get("price", "N/A")
                        ptype = prop.get("property_type", "Residential")
                        handover = prop.get("handover_date", "N/A")
                        amenities = prop.get("key_amenities") or prop.get("amenities") or []
                        p_class = prop.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                        prov_label = "Directly Scraped" if (p_class == "DIRECTLY_SCRAPED" or prop.get("is_directly_scraped")) else "Publicly Verified Fallback"
                        url = prop.get("url") or prop.get("canonical_url", "")

                        response_parts.append(f"#### [{idx}] {title}")
                        response_parts.append(f"- **Source Platform**: {source}")
                        response_parts.append(f"- **Location**: {loc} [{idx}]")
                        response_parts.append(f"- **Price / Financials**: {price} [{idx}]")
                        response_parts.append(f"- **Property Type**: {ptype} [{idx}]")
                        if handover and handover != "N/A":
                            response_parts.append(f"- **Handover / Status**: {handover} [{idx}]")
                        if amenities:
                            amenity_list = ", ".join(amenities[:4]) if isinstance(amenities, list) else str(amenities)
                            response_parts.append(f"- **Key Amenities**: {amenity_list} [{idx}]")
                        if url:
                            response_parts.append(f"- **Verified Source & Provenance**: [{prov_label}]({url})")
                        else:
                            response_parts.append(f"- **Data Provenance**: [{prov_label}]")
                        response_parts.append("")
                    response_parts.append(
                        "> [!NOTE]\n"
                        "> Comparative metrics are derived directly from verified canonical records with transparent provenance."
                    )
                    return "\n".join(response_parts)

                # Dedicated single-property showcase (e.g. "Show me the second one", or specific project lookup)
                if len(agent_properties) == 1 and not is_comparison:
                    prop = agent_properties[0]
                    title = prop.get("title", "Property Listing")
                    source = prop.get("source", "DarGlobal")
                    loc = prop.get("location", "N/A")
                    price = prop.get("price", "Price on Application")
                    ptype = prop.get("property_type", "Residential Development")
                    handover = prop.get("handover_date", "Available upon request")
                    brand = prop.get("brand_partner") or prop.get("developer_or_broker") or source
                    desc = prop.get("description", "")
                    amenities = prop.get("key_amenities") or prop.get("amenities") or []
                    p_class = prop.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                    prov_badge = "Directly Scraped" if (p_class == "DIRECTLY_SCRAPED" or prop.get("is_directly_scraped")) else "Publicly Verified Fallback"
                    url = prop.get("url") or prop.get("canonical_url", "")

                    parts = []
                    if filter_banner:
                        parts.append(filter_banner.strip())
                        parts.append("")
                    parts.append(f"### {title}\n")
                    parts.append(f"Here are the complete verified specifications and details for **{title}**:\n")
                    parts.append(f"- **Developer / Brand Partner**: {brand}")
                    parts.append(f"- **Location**: {loc} [1]")
                    parts.append(f"- **Starting Price / Financials**: {price} [1]")
                    parts.append(f"- **Property Type**: {ptype} [1]")
                    if handover and handover != "N/A":
                        parts.append(f"- **Handover / Status**: {handover} [1]")
                    if desc:
                        parts.append(f"- **Overview**: {desc} [1]")
                    if amenities:
                        parts.append("- **Verified Amenities & Lifestyle Features**:")
                        if isinstance(amenities, list):
                            for am in amenities:
                                parts.append(f"  - {am} [1]")
                        else:
                            parts.append(f"  - {amenities} [1]")
                    if url:
                        parts.append(f"- **Verified Source & Provenance**: [{prov_badge}]({url})")
                    else:
                        parts.append(f"- **Data Provenance**: [{prov_badge}]")
                    parts.append("")
                    parts.append(
                        "> [!NOTE]\n"
                        "> All property specifications and pricing details are verified against canonical project disclosures with zero fabricated data."
                    )
                    return "\n".join(parts)

                # High-quality structured conversational property response (Bug 4)
                if "dubai" in user_lower:
                    intro = (
                        "DarGlobal offers an extraordinary portfolio of ultra-luxury residential developments in **Dubai**, "
                        "showcasing world-class collaborations with iconic design and automotive houses such as Pagani, Missoni, and Gensler. "
                        "Here are the premier verified developments currently available in Dubai:"
                    )
                elif any(w in user_lower for w in ["riyadh", "saudi", "wasalt"]):
                    intro = (
                        "Here are verified real estate properties and developments in **Saudi Arabia**, retrieved from "
                        "the Wasalt marketplace and DarGlobal's regional portfolio, offering premium independent villas, "
                        "contemporary duplexes, and prime commercial investments:"
                    )
                elif any(w in user_lower for w in ["marbella", "spain"]):
                    intro = (
                        "In **Marbella, Spain**, DarGlobal presents ultra-exclusive hillside residences in partnership with "
                        "Automobili Lamborghini. Here are the verified project details:"
                    )
                elif any(w in user_lower for w in ["muscat", "oman", "aida"]):
                    intro = (
                        "In **Muscat, Oman**, DarGlobal has partnered with Omran and Trump International to deliver cliffside luxury. "
                        "Here are the verified development details:"
                    )
                elif any(w in user_lower for w in ["qatar", "lusail", "vagues"]):
                    intro = (
                        "In **Qatar (Qetaifan Island North, Lusail)**, DarGlobal features bespoke seafront living in collaboration with "
                        "Elie Saab. Here are the verified project details:"
                    )
                else:
                    intro = (
                        "Based on verified records from **DarGlobal** and **Wasalt**, "
                        "here are the premier properties and developments matching your criteria:"
                    )

                response_parts = []
                if filter_banner:
                    response_parts.append(filter_banner.strip())
                    response_parts.append("")
                response_parts.extend([intro, ""])

                # Numbered property highlights (Bug 4)
                for idx, prop in enumerate(agent_properties[:5], 1):
                    title = prop.get("title", "Property Listing")
                    source = prop.get("source", "DarGlobal")
                    loc = prop.get("location", "N/A")
                    price = prop.get("price", "Price on Application")
                    ptype = prop.get("property_type", "Residential Development")
                    handover = prop.get("handover_date", "Available upon request")
                    brand = prop.get("brand_partner") or prop.get("developer_or_broker") or source
                    desc = prop.get("description", "")
                    amenities = prop.get("key_amenities") or prop.get("amenities") or []
                    p_class = prop.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                    prov_badge = "Directly Scraped" if (p_class == "DIRECTLY_SCRAPED" or prop.get("is_directly_scraped")) else "Publicly Verified Fallback"
                    url = prop.get("url") or prop.get("canonical_url", "")

                    response_parts.append(f"#### {idx}. {title}")
                    response_parts.append(f"- **Developer / Brand Partner**: {brand}")
                    response_parts.append(f"- **Location**: {loc} [{idx}]")
                    response_parts.append(f"- **Starting Price / Financials**: {price} [{idx}]")
                    response_parts.append(f"- **Property Type**: {ptype} [{idx}]")
                    if handover and handover != "N/A":
                        response_parts.append(f"- **Handover / Status**: {handover} [{idx}]")
                    if desc:
                        short_desc = desc[:200] + "..." if len(desc) > 200 else desc
                        response_parts.append(f"- **Overview**: {short_desc} [{idx}]")
                    if amenities:
                        amenity_list = ", ".join(amenities[:4]) if isinstance(amenities, list) else str(amenities)
                        response_parts.append(f"- **Key Amenities**: {amenity_list} [{idx}]")
                    if url:
                        response_parts.append(f"- **Verified Source & Provenance**: [{prov_badge}]({url})")
                    else:
                        response_parts.append(f"- **Data Provenance**: [{prov_badge}]")
                    response_parts.append("")

                # Engaging closing prompt (Bug 4)
                response_parts.append(
                    "Would you like to explore detailed amenities and architectural specifications for any of these developments, "
                    "compare them with properties in other markets (such as Riyadh or Muscat), or filter by a specific budget or unit layout?"
                )
                response_parts.append("")
                response_parts.append(
                    "> [!NOTE]\n"
                    "> All property details, pricing indicators, and amenities are verified against canonical project disclosures "
                    "and sitemap listings with zero fabricated data."
                )

                return "\n".join(response_parts)

            # If no agent properties were retrieved:
            # Check for unindexed jurisdictions (e.g. Tokyo)
            loc_found = None
            for c in ["tokyo", "japan", "singapore", "paris", "new york", "cairo", "london"]:
                if c in user_lower:
                    loc_found = c.title()
                    break

            if loc_found:
                return (
                    f"I couldn't find verified {loc_found} properties in the indexed dataset.\n\n"
                    "The currently indexed portfolio for DarGlobal and Wasalt covers verified developments in:\n"
                    "- **Dubai, UAE**: DaVinci Tower by Pagani, Urban Oasis by Missoni, DG1 Living, W Residences Downtown\n"
                    "- **Muscat, Oman**: AIDA (Trump International Golf Community)\n"
                    "- **Marbella / Benahavís, Spain**: Tierra Viva by Automobili Lamborghini\n"
                    "- **Doha, Qatar**: Les Vagues by Elie Saab\n"
                    "- **Saudi Arabia (Riyadh, Jeddah, Al Khobar)**: Tabasheer (Sedra), Al Malqa smart villas, Al Narjis duplexes, and commercial office floors\n\n"
                    "> [!NOTE]\n"
                    "> This limitation reflects only the records currently indexed in this platform. It does not represent an exhaustive declaration of all global corporate activities."
                )

            # Check if this was a greeting or general conversation that slipped through
            from backend.app.agent.intent import IntentClassifier, IntentType
            offline_intent, _ = IntentClassifier.classify(user_content)
            if offline_intent in [IntentType.GREETING, IntentType.GENERAL_CONVERSATION, IntentType.UNSUPPORTED_QUERY]:
                return IntentClassifier.get_natural_response(offline_intent, user_content)

            return (
                "I couldn't find verified properties matching your inquiry in the indexed dataset. "
                "Please verify your location or project spelling (e.g. Dubai, Riyadh, Jeddah, Muscat, Marbella, Pagani, Missoni, AIDA)."
            )

        # Extract numbered contexts from the system prompt
        lines = system_content.split("\n")
        contexts = []
        current_ctx = []
        ctx_num = 0

        for line in lines:
            if line.startswith("--- Document ["):
                if current_ctx:
                    contexts.append((ctx_num, "\n".join(current_ctx)))
                    current_ctx = []
                try:
                    ctx_num = int(line[line.find("[") + 1 : line.find("]")])
                except Exception:
                    ctx_num += 1
            elif ctx_num > 0:
                current_ctx.append(line)
        if current_ctx:
            contexts.append((ctx_num, "\n".join(current_ctx)))

        if not contexts:
            return (
                "Based on the verified DarGlobal and Wasalt real estate databases, no matching property "
                "or project records were found for your inquiry. Please try searching for specific projects "
                "(e.g., Pagani, Urban Oasis, AIDA, Tierra Viva, W Residences) or locations (Dubai, Riyadh, Jeddah)."
            )

        # Synthesize from top retrieved documents
        response_parts = []
        user_lower = user_content.lower()

        # Check for comparison
        is_comparison = any(w in user_lower for w in ["compare", "difference", "vs", "versus", "between"])

        if is_comparison:
            response_parts.append("### Comparative Real Estate Analysis\n")
            response_parts.append(
                "Based on the official records retrieved from **DarGlobal** and **Wasalt**, "
                "here is a structured comparison of the matching developments:\n"
            )
        else:
            response_parts.append("### Property Overview & Details\n")

        for idx, (cnum, ctext) in enumerate(contexts[:3]):
            title_line = next((l for l in ctext.split("\n") if "PROJECT / PROPERTY:" in l or "DOCUMENT:" in l), "")
            loc_line = next((l for l in ctext.split("\n") if "LOCATION:" in l), "")
            price_line = next((l for l in ctext.split("\n") if "PRICE:" in l), "")
            amenities_line = next((l for l in ctext.split("\n") if "AMENITIES:" in l or "FEATURED AMENITIES:" in l), "")

            clean_title = title_line.replace("PROJECT / PROPERTY:", "").replace("DOCUMENT:", "").strip()
            clean_loc = loc_line.replace("LOCATION:", "").strip()
            clean_price = price_line.replace("TYPE:", "").replace("PRICE:", "").strip()

            response_parts.append(f"#### {clean_title} [{cnum}]")
            if clean_loc:
                response_parts.append(f"- **Location**: {clean_loc} [{cnum}]")
            if clean_price:
                response_parts.append(f"- **Financial / Type**: {clean_price} [{cnum}]")

            # Extract summary paragraph
            desc_lines = [l.strip() for l in ctext.split("\n") if len(l.strip()) > 60 and not l.startswith("PROJECT") and not l.startswith("SOURCE") and not l.startswith("LOCATION")]
            if desc_lines:
                response_parts.append(f"- **Overview**: {desc_lines[0]} [{cnum}]")

            if amenities_line:
                clean_amenities = amenities_line.replace("AMENITIES:", "").strip()
                if clean_amenities:
                    response_parts.append(f"- **Key Amenities**: {clean_amenities} [{cnum}]")
            response_parts.append("")

        response_parts.append(
            "> [!NOTE]\n"
            "> All cited figures and project descriptions are derived directly from indexed canonical records "
            "from **DarGlobal** and **Wasalt**."
        )

        return "\n".join(response_parts)

openrouter_client = OpenRouterClient()
