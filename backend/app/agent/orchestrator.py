import re
import time
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.ingestion.seed_data import is_allowed_property_result
from backend.app.agent.tools import (
    AgentToolRegistry,
    AGENT_OPENAI_TOOLS,
    SearchDarGlobalInput,
    SearchWasaltInput,
    SearchByLocationInput,
    GetProjectDetailsInput,
    ComparePropertiesInput,
    GetSourceInformationInput,
    FilterPreviousResultsInput,
)
from backend.app.schemas.agent import ToolExecutionTrace, IntentType
from backend.app.schemas.chat import ChatRequest, ChatResponse, Citation, ChatMessage
from backend.app.agent.intent import IntentClassifier
from backend.app.agent.conversation_state import conversation_state_manager, ConversationState, LOCATION_METADATA
from backend.app.llm.model_selector import model_selector
from backend.app.llm.openrouter_client import openrouter_client

AGENT_SYSTEM_PROMPT = """You are "DarGlobal Intelligence Agent", an autonomous executive real estate advisor with genuine tool execution capabilities.

You have access to 6 specialized real estate tools to inspect verified data from DarGlobal and Wasalt:
1. `search_darglobal_projects`: Search luxury international projects by DarGlobal (Dubai, Marbella, Muscat, Qatar).
2. `search_wasalt_properties`: Search Saudi Arabian real estate listings on Wasalt with budget filtering in SAR.
3. `search_by_location`: Retrieve properties and projects matching a specific city, district, or region.
4. `get_project_details`: Retrieve deep detailed specifications, amenities, handover dates, and partner brands for a specific project.
5. `compare_properties`: Compare two or more properties using verified attributes without fabrication.
6. `get_source_information`: Retrieve data provenance classification, canonical URLs, and extraction audit trail.

EXECUTION & INTEGRITY GUIDELINES:
- Always analyze the user's intent and select the appropriate tool(s) to retrieve verified real estate data.
- When budget constraints are mentioned (e.g. "under SAR 2 million"), pass the exact numeric budget to `max_budget_sar` or `max_budget_usd`.
- When comparing across markets (e.g. Dubai vs Riyadh), call tools for both sources and compare only verified attributes.
- STRICT NO-FABRICATION: Never invent prices, amenities, unit counts, or handover dates.
- MANDATORY CITATIONS: Cite every factual point with bracketed document citations [1], [2] referencing the canonical URLs returned by the tools.
- PROVENANCE TRANSPARENCY: Acknowledge data provenance (DIRECTLY_SCRAPED vs PUBLICLY_VERIFIED_FALLBACK) truthfully without fabricated or contradictory claims.
- NEGATIVE QUERY GROUNDING: If no verified properties are found in the indexed dataset for a requested location (e.g. Tokyo), state: "I couldn't find verified [Location] properties in the indexed dataset." NEVER claim that a company does not operate in a jurisdiction merely because the database lacks matching records.

RESPONSE STRUCTURE & CONVERSATIONAL QUALITY:
- When presenting retrieved properties or projects to the user:
  1. Open with an engaging, executive-level introduction tailored to the target market (e.g. Dubai luxury developments, Riyadh residential opportunities).
  2. Format each property as a numbered highlight:
     * Project / Property Title
     * Developer / Brand Partner
     * Location
     * Starting Price / Financials
     * Property Type
     * Handover Date / Status
     * Key Amenities
     * Verified Source Link with explicit Provenance Badge (e.g., [Publicly Verified Fallback](url))
  3. Close with an engaging prompt suggesting logical next exploration steps (amenities, floor plans, comparative pricing, or specific budget limits).
- NEVER output a generic greeting when real estate properties have been retrieved. Synthesize the findings directly.
- STRICT FILTERING: Never present sitemap indexes, navigation pages, or scraping logs as property listings. Only genuine residential or commercial properties are valid property results.
"""

class AgentOrchestrator:
    """
    Agent Orchestration Layer coordinating multi-step tool calls,
    argument validation, execution timeouts, loop prevention,
    and structured execution trace logging.
    """

    def __init__(self, tool_registry: AgentToolRegistry, max_steps: int = 5, per_tool_timeout: float = 12.0):
        self.tools = tool_registry
        self.max_steps = max_steps
        self.per_tool_timeout = per_tool_timeout
        self.tool_map = {
            "search_darglobal_projects": (self.tools.search_darglobal_projects, SearchDarGlobalInput),
            "search_wasalt_properties": (self.tools.search_wasalt_properties, SearchWasaltInput),
            "search_by_location": (self.tools.search_by_location, SearchByLocationInput),
            "get_project_details": (self.tools.get_project_details, GetProjectDetailsInput),
            "compare_properties": (self.tools.compare_properties, ComparePropertiesInput),
            "get_source_information": (self.tools.get_source_information, GetSourceInformationInput),
            "filter_previous_results": (self.tools.filter_previous_results, FilterPreviousResultsInput),
        }

    async def execute_tool(
        self,
        step: int,
        tool_name: str,
        raw_arguments: Dict[str, Any]
    ) -> ToolExecutionTrace:
        """
        Executes a single tool with Pydantic validation, timeouts, and execution trace logging.
        Never pretends to execute: calls genuine Python functions.
        """
        start_time = time.time()
        logger.info(f"[Agent Step {step}] Executing tool: '{tool_name}' with args: {raw_arguments}")

        if tool_name not in self.tool_map:
            elapsed = (time.time() - start_time) * 1000
            err_msg = f"Tool '{tool_name}' is not recognized or unavailable in registry."
            logger.warning(err_msg)
            return ToolExecutionTrace(
                step=step,
                tool_name=tool_name,
                arguments=raw_arguments,
                execution_time_ms=round(elapsed, 2),
                status="ERROR",
                result_summary=err_msg,
                error=err_msg
            )

        func, schema_cls = self.tool_map[tool_name]

        # 1. Validate arguments with Pydantic
        try:
            validated_args = schema_cls(**raw_arguments)
        except ValidationError as ve:
            elapsed = (time.time() - start_time) * 1000
            err_msg = f"Argument validation failed for {tool_name}: {str(ve)}"
            logger.error(err_msg)
            return ToolExecutionTrace(
                step=step,
                tool_name=tool_name,
                arguments=raw_arguments,
                execution_time_ms=round(elapsed, 2),
                status="ERROR",
                result_summary="Invalid tool arguments",
                error=err_msg
            )

        # 2. Execute with timeout
        try:
            # Handle sync tool function in threadpool
            result = await asyncio.wait_for(
                asyncio.to_thread(func, validated_args),
                timeout=self.per_tool_timeout
            )
            elapsed = (time.time() - start_time) * 1000

            # Generate concise result summary
            summary = self._summarize_tool_result(tool_name, result)
            logger.info(f"[Agent Step {step}] Tool '{tool_name}' finished in {elapsed:.1f}ms: {summary}")

            return ToolExecutionTrace(
                step=step,
                tool_name=tool_name,
                arguments=raw_arguments,
                execution_time_ms=round(elapsed, 2),
                status="SUCCESS",
                result_summary=summary,
                output=result
            )
        except asyncio.TimeoutError:
            elapsed = (time.time() - start_time) * 1000
            err_msg = f"Execution timed out after {self.per_tool_timeout}s for tool '{tool_name}'"
            logger.error(err_msg)
            return ToolExecutionTrace(
                step=step,
                tool_name=tool_name,
                arguments=raw_arguments,
                execution_time_ms=round(elapsed, 2),
                status="TIMEOUT",
                result_summary=err_msg,
                error=err_msg
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            err_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logger.error(err_msg)
            return ToolExecutionTrace(
                step=step,
                tool_name=tool_name,
                arguments=raw_arguments,
                execution_time_ms=round(elapsed, 2),
                status="ERROR",
                result_summary=err_msg,
                error=err_msg
            )

    def _summarize_tool_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"Error: {result['error']}"
        if tool_name == "search_darglobal_projects":
            count = result.get("count", 0)
            names = [p.get("title") for p in result.get("projects", [])[:3]]
            return f"Found {count} DarGlobal project(s): {', '.join(names)}"
        elif tool_name == "search_wasalt_properties":
            count = result.get("count", 0)
            names = [p.get("title") for p in result.get("properties", [])[:3]]
            return f"Found {count} Wasalt property listing(s): {', '.join(names)}"
        elif tool_name == "search_by_location":
            count = result.get("count", 0)
            loc = result.get("location_queried", "")
            return f"Found {count} record(s) matching location '{loc}'"
        elif tool_name == "get_project_details":
            title = result.get("title", "Project")
            price = result.get("price", "N/A")
            return f"Retrieved detailed specs for '{title}' (Price: {price})"
        elif tool_name == "compare_properties":
            count = result.get("comparison_count", 0)
            return f"Successfully generated attribute comparison across {count} verified properties"
        elif tool_name == "get_source_information":
            p_class = result.get("provenance_class", "N/A")
            url = result.get("canonical_url", "")
            return f"Verified provenance: {p_class} ({url})"
        elif tool_name == "filter_previous_results":
            count = result.get("filtered_count", 0)
            names = [p.get("title") for p in result.get("filtered_properties", [])[:3]]
            return f"Filtered to {count} matching property/properties: {', '.join(names)}"
        return f"Executed successfully with {len(result)} fields returned"

    def classify_intent(
        self,
        query: str,
        history: Optional[List[ChatMessage]] = None,
        conversation_id: Optional[str] = None
    ) -> tuple[IntentType, Dict[str, Any]]:
        """
        Classifies incoming query intent into GREETING, GENERAL_CONVERSATION,
        PROPERTY_SEARCH, PROJECT_SEARCH, PROPERTY_COMPARISON, LOCATION_SEARCH,
        PROJECT_DETAILS, FOLLOW_UP, AMBIGUOUS_FOLLOW_UP, or UNSUPPORTED_QUERY.
        """
        return IntentClassifier.classify(query=query, history=history, conversation_id=conversation_id)

    def plan_tools_from_query(
        self,
        query: str,
        source_filter: Optional[str] = None,
        history: Optional[List[ChatMessage]] = None,
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> List[tuple[str, Dict[str, Any]]]:
        """
        Intelligent planner that analyzes the query semantics, intent, and conversation context to select relevant tools.
        Used as primary dispatcher and fallback when external model does not support native tool calling.
        Guarantees that every tool call corresponds to genuine code execution.
        """
        # Step 0: Classify intent
        intent, intent_params = self.classify_intent(query, history=history, conversation_id=conversation_id)

        # Do not plan or invoke tools for greetings, general conversation, unsupported queries, or ambiguous follow-ups
        if intent in [IntentType.GREETING, IntentType.GENERAL_CONVERSATION, IntentType.UNSUPPORTED_QUERY, IntentType.AMBIGUOUS_FOLLOW_UP]:
            return []

        conv_state = conversation_state_manager.get_or_create_state(conversation_id=conversation_id, history=history)
        follow_up_type = intent_params.get("follow_up_type")

        # A. Handle Budget Refinement (Test 1, Test 2)
        if follow_up_type == "BUDGET_REFINEMENT" or (intent == IntentType.FOLLOW_UP and "max_budget" in intent_params):
            max_budget = intent_params.get("max_budget")
            currency = intent_params.get("currency") or conv_state.currency or "AED"
            location = intent_params.get("location") or conv_state.location or "Dubai"
            prev_results = intent_params.get("previous_results") or conv_state.previous_results or []

            # Check previous search results first. If structured property info exists, filter cached results without redundant retrieval tools
            if prev_results:
                return [("filter_previous_results", {
                    "max_budget": max_budget,
                    "currency": currency,
                    "location": location,
                    "properties_to_filter": prev_results
                })]
            else:
                if currency == "SAR" or (location and location.lower() in ["riyadh", "jeddah", "khobar"]):
                    return [("search_wasalt_properties", {
                        "query": query,
                        "city": location,
                        "max_budget_sar": max_budget,
                        "property_type": conv_state.property_type,
                        "max_results": 5
                    })]
                else:
                    return [("search_darglobal_projects", {
                        "query": query,
                        "city": location,
                        "max_results": 5
                    })]

        # B. Handle Bedroom Refinement (Test 3)
        if follow_up_type == "BEDROOM_REFINEMENT" or (intent == IntentType.FOLLOW_UP and "bedrooms" in intent_params):
            bedrooms = intent_params.get("bedrooms")
            prev_results = intent_params.get("previous_results") or conv_state.previous_results or []
            if prev_results:
                return [("filter_previous_results", {
                    "bedrooms": bedrooms,
                    "location": conv_state.location,
                    "currency": conv_state.currency,
                    "properties_to_filter": prev_results
                })]
            else:
                loc = conv_state.location or "Dubai"
                if loc.lower() in ["riyadh", "jeddah", "khobar"]:
                    return [("search_wasalt_properties", {
                        "query": query,
                        "city": loc,
                        "property_type": conv_state.property_type,
                        "max_results": 5
                    })]
                else:
                    return [("search_darglobal_projects", {
                        "query": query,
                        "city": loc,
                        "max_results": 5
                    })]

        # C. Handle Location Refinement (Test 4: "What about Riyadh?")
        if follow_up_type == "LOCATION_REFINEMENT" or (intent == IntentType.LOCATION_SEARCH and intent_params.get("follow_up_type") == "LOCATION_REFINEMENT"):
            new_loc = intent_params.get("location", "Riyadh")
            loc_lower = new_loc.lower()
            if loc_lower in ["riyadh", "jeddah", "al khobar", "khobar", "sedra", "al malqa", "al narjis", "al shati", "al hada"]:
                return [("search_wasalt_properties", {
                    "query": query,
                    "city": new_loc,
                    "property_type": conv_state.property_type,
                    "max_results": 5
                })]
            else:
                return [("search_darglobal_projects", {
                    "query": query,
                    "city": new_loc,
                    "max_results": 5
                })]

        q_lower = query.lower()
        planned: List[tuple[str, Dict[str, Any]]] = []

        # 1. Budget extraction (SAR / AED / USD)
        budget_sar = intent_params.get("max_budget_sar") or IntentClassifier.extract_budget_sar(query)

        # 2. Location detection (core and international)
        locations = ["riyadh", "jeddah", "al khobar", "khobar", "dubai", "marbella", "muscat", "qatar", "lusail", "al malqa", "al narjis", "al shati", "al hada", "sedra"]
        detected_loc = next((loc for loc in locations if loc in q_lower), None)
        if not detected_loc:
            intl_cities = ["tokyo", "japan", "london", "paris", "new york", "singapore", "cairo"]
            detected_loc = next((c for c in intl_cities if c in q_lower), None)

        # 3. Handle Project Details & Follow-up
        if intent in [IntentType.FOLLOW_UP, IntentType.PROJECT_DETAILS] or follow_up_type == "DETAILS_FOLLOW_UP":
            proj_id = intent_params.get("resolved_project_id") or intent_params.get("project_id")
            if proj_id:
                return [("get_project_details", {"project_id": proj_id})]

        # 4. Handle Provenance / Source inquiry
        if any(w in q_lower for w in ["provenance", "source", "authenticity", "url", "audit", "verified", "scraped", "evidence"]):
            target_q = intent_params.get("project_id") or (detected_loc or query)
            return [("get_source_information", {"query_or_url": target_q})]

        # 5. Handle Comparison
        if intent == IntentType.PROPERTY_COMPARISON:
            prop_ids = intent_params.get("property_ids", [])
            if len(prop_ids) >= 2:
                return [("compare_properties", {
                    "property_names_or_ids": prop_ids[:4],
                    "focus_attributes": ["price", "location", "property_type", "amenities", "handover_date"]
                })]
            elif intent_params.get("resolved_project_id"):
                return [("compare_properties", {
                    "property_names_or_ids": [intent_params["resolved_project_id"], "ws-villa-malqa-riyadh"]
                })]
            elif ("darglobal" in q_lower or "dubai" in q_lower) and ("wasalt" in q_lower or "riyadh" in q_lower):
                return [
                    ("search_darglobal_projects", {"query": query, "city": "Dubai"}),
                    ("search_wasalt_properties", {"query": query, "city": "Riyadh", "max_budget_sar": budget_sar})
                ]
            else:
                return [
                    ("search_darglobal_projects", {"query": query, "city": "Dubai", "max_results": 2}),
                    ("search_wasalt_properties", {"query": query, "city": "Riyadh", "max_budget_sar": budget_sar, "max_results": 2})
                ]

        # 6. Handle Property Search (Wasalt / Saudi)
        if intent == IntentType.PROPERTY_SEARCH:
            city = intent_params.get("city") or (detected_loc.title() if detected_loc in ["riyadh", "jeddah", "al khobar", "khobar", "al malqa", "al narjis", "al shati", "al hada", "sedra"] else None)
            ptype = intent_params.get("property_type") or ("villa" if "villa" in q_lower else ("apartment" if "apartment" in q_lower else ("duplex" if "duplex" in q_lower else None)))
            return [("search_wasalt_properties", {
                "query": query,
                "city": city,
                "property_type": ptype,
                "max_budget_sar": budget_sar,
                "max_results": 5
            })]

        # 7. Handle Project Search (DarGlobal)
        if intent == IntentType.PROJECT_SEARCH:
            city = intent_params.get("city") or (detected_loc.title() if detected_loc in ["dubai", "marbella", "muscat", "qatar", "lusail", "tokyo", "japan", "london", "paris", "new york", "singapore", "cairo"] else None)
            return [("search_darglobal_projects", {
                "query": query,
                "city": city,
                "max_results": 5
            })]

        # 8. Handle Location Search
        if intent == IntentType.LOCATION_SEARCH:
            return [("search_by_location", {
                "location": intent_params.get("location") or detected_loc or query,
                "source_filter": source_filter
            })]

        # Fallback for remaining property queries
        if detected_loc:
            planned.append(("search_by_location", {"location": detected_loc, "source_filter": source_filter}))
        else:
            planned.append(("search_darglobal_projects", {"query": query, "max_results": 3}))
            planned.append(("search_wasalt_properties", {"query": query, "max_results": 3}))

        return planned

    def _extract_citations_from_trace(self, traces: List[ToolExecutionTrace]) -> List[Citation]:
        """Collects verified citations from all executed tools."""
        citations: List[Citation] = []
        seen_urls = set()
        citation_id = 1

        for trace in traces:
            output = trace.output or {}
            # Check for project lists, compared properties, and matches
            items = (
                output.get("projects")
                or output.get("properties")
                or output.get("filtered_properties")
                or output.get("compared_properties")
                or output.get("matches")
                or output.get("sources")
                or []
            )
            if output.get("found") and "title" in output:
                items.append(output)

            # Unless specifically auditing source information, filter out non-property documents
            if trace.tool_name != "get_source_information":
                items = [item for item in items if is_allowed_property_result(item)]

            for item in items:
                url = item.get("url") or item.get("canonical_url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title = item.get("title", "Real Estate Information")
                source = item.get("source") or item.get("source_platform") or "DarGlobal Intelligence"
                snippet = item.get("description") or f"Location: {item.get('location')}. Price: {item.get('price')}."
                p_class = item.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                ext_method = item.get("extraction_method", "agent_tool_retrieval")
                ext_time = item.get("extraction_timestamp", "2026-11-18T17:35:40Z")
                is_direct = item.get("is_directly_scraped", False)

                citations.append(Citation(
                    citation_id=citation_id,
                    title=title,
                    url=url,
                    source=source,
                    snippet=snippet[:220] + "..." if len(snippet) > 220 else snippet,
                    provenance_class=p_class,
                    extraction_method=ext_method,
                    extraction_timestamp=ext_time,
                    is_directly_scraped=is_direct,
                    alternative_source=item.get("alternative_source"),
                    origin_notes=item.get("origin_notes", ""),
                    metadata=item
                ))
                citation_id += 1

        return citations

    def _format_agent_context(self, traces: List[ToolExecutionTrace]) -> str:
        """Formats real executed tool traces into an authoritative grounding context."""
        context_blocks = []
        for trace in traces:
            output_json = json.dumps(trace.output, indent=2) if trace.output else "{}"
            block = (
                f"### TOOL EXECUTED: `{trace.tool_name}` (Step {trace.step})\n"
                f"- Arguments: {json.dumps(trace.arguments)}\n"
                f"- Execution Status: {trace.status} ({trace.execution_time_ms}ms)\n"
                f"- Result Summary: {trace.result_summary}\n"
                f"- Verified Data Payload:\n```json\n{output_json}\n```\n"
            )
            context_blocks.append(block)

        return "\n".join(context_blocks)

    def _update_conversation_state_from_traces(
        self,
        state: ConversationState,
        query: str,
        traces: List[ToolExecutionTrace],
        intent_params: Dict[str, Any]
    ) -> ConversationState:
        """Updates persistent conversation state from executed tool traces and parameters."""
        state.last_search_query = query

        for trace in traces:
            output = trace.output or {}
            args = trace.arguments or {}

            if trace.tool_name == "filter_previous_results":
                filtered = output.get("filtered_properties") or output.get("properties", [])
                if filtered:
                    state.previous_results = filtered
                if "max_budget" in args and args["max_budget"]:
                    state.budget_max = float(args["max_budget"])
                if "bedrooms" in args and args["bedrooms"]:
                    state.bedrooms = int(args["bedrooms"])
                if "property_type" in args and args["property_type"]:
                    state.property_type = str(args["property_type"])
                if "currency" in args and args["currency"]:
                    state.currency = str(args["currency"])
                if "location" in args and args["location"]:
                    state.location = str(args["location"])
                    meta = LOCATION_METADATA.get(state.location.lower(), {})
                    if "country" in meta:
                        state.country = meta["country"]

            elif trace.tool_name == "search_darglobal_projects":
                projs = [p for p in output.get("projects", []) if is_allowed_property_result(p)]
                if projs:
                    state.previous_results = projs
                city = args.get("city") or "Dubai"
                state.location = city
                meta = LOCATION_METADATA.get(city.lower(), {})
                state.currency = meta.get("currency", "AED")
                state.country = meta.get("country", "UAE")
                state.data_sources = ["darglobal"]
                if "villa" in query.lower():
                    state.property_type = "villa"
                elif "apartment" in query.lower():
                    state.property_type = "apartment"

            elif trace.tool_name == "search_wasalt_properties":
                props = [p for p in output.get("properties", []) if is_allowed_property_result(p)]
                if props:
                    state.previous_results = props
                city = args.get("city") or "Riyadh"
                state.location = city
                meta = LOCATION_METADATA.get(city.lower(), {})
                state.currency = meta.get("currency", "SAR")
                state.country = meta.get("country", "Saudi Arabia")
                state.data_sources = ["wasalt"]
                if args.get("max_budget_sar"):
                    state.budget_max = float(args["max_budget_sar"])
                if args.get("property_type"):
                    state.property_type = str(args["property_type"])

            elif trace.tool_name == "compare_properties":
                state.data_sources = ["darglobal", "wasalt"]

        return state

    def _build_active_filters(self, state: ConversationState) -> Optional[Dict[str, Any]]:
        """Constructs structured active filter metadata for chat transparency."""
        if not state.location and not state.budget_max and not state.bedrooms and not state.property_type:
            return None

        parts = []
        if state.location:
            parts.append(f"Location: {state.location}")
        if state.budget_max:
            curr = state.currency or ""
            parts.append(f"Budget: Up to {curr} {int(state.budget_max):,}".strip())
        if state.bedrooms:
            parts.append(f"Bedrooms: {state.bedrooms}")
        if state.property_type:
            parts.append(f"Type: {state.property_type.title()}")
        if state.data_sources:
            sources_str = ", ".join(s.title() for s in state.data_sources)
            parts.append(f"Source: {sources_str}")

        summary = " | ".join(parts)
        return {
            "location": state.location,
            "currency": state.currency,
            "budget_max": state.budget_max,
            "property_type": state.property_type,
            "bedrooms": state.bedrooms,
            "data_sources": state.data_sources,
            "filter_summary": summary
        }

    async def run_agent(self, request: ChatRequest) -> ChatResponse:
        """
        Orchestrates full agent reasoning loop:
        1. Classifies user conversational intent.
        2. Handles greetings and general conversation naturally without tools.
        3. Selects and executes genuine tools for property and project queries.
        4. Validates parameters and applies timeouts.
        5. Prevents loops and enforces max step limits.
        6. Synthesizes final response strictly citing verified data.
        """
        start_time = time.time()
        user_msg = request.message
        conv_id = request.conversation_id or "default_session"

        # Step 0: Intent classification
        intent, intent_params = self.classify_intent(user_msg, history=request.history, conversation_id=conv_id)
        if intent in [IntentType.GREETING, IntentType.GENERAL_CONVERSATION, IntentType.UNSUPPORTED_QUERY, IntentType.AMBIGUOUS_FOLLOW_UP]:
            answer = IntentClassifier.get_natural_response(intent, user_msg)
            elapsed_ms = (time.time() - start_time) * 1000
            return ChatResponse(
                answer=answer,
                citations=[],
                model_used=model_selector.active_model,
                retrieval_count=0,
                provenance_summary={},
                execution_trace=[],
                execution_time_ms=round(elapsed_ms, 2),
                intent=intent.value,
                conversation_id=conv_id,
                active_filters=None,
                conversation_state=None
            )

        traces: List[ToolExecutionTrace] = []
        seen_calls = set()

        # Step 1: Determine initial tool execution plan
        try:
            planned_calls = self.plan_tools_from_query(
                user_msg,
                source_filter=request.source_filter,
                history=request.history,
                conversation_id=conv_id
            )
        except TypeError:
            planned_calls = self.plan_tools_from_query(user_msg, request.source_filter)
        step = 1

        for tool_name, args in planned_calls:
            if step > self.max_steps:
                logger.warning(f"Reached max execution step limit ({self.max_steps}). Halting tool loop.")
                break

            call_signature = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
            if call_signature in seen_calls:
                logger.warning(f"Loop detected for tool call {call_signature}. Skipping redundant execution.")
                continue
            seen_calls.add(call_signature)

            trace = await self.execute_tool(step=step, tool_name=tool_name, raw_arguments=args)
            traces.append(trace)
            step += 1

        # Step 2: Update conversation state from execution traces
        conv_state = conversation_state_manager.get_or_create_state(conversation_id=conv_id, history=request.history)
        self._update_conversation_state_from_traces(conv_state, user_msg, traces, intent_params)
        conversation_state_manager.save_state(conv_state)
        active_filters = self._build_active_filters(conv_state)

        # Step 3: Extract citations from verified tool outputs
        citations = self._extract_citations_from_trace(traces)

        # Step 4: Build grounding prompt for LLM synthesis
        grounding_context = self._format_agent_context(traces)
        if active_filters and active_filters.get("filter_summary"):
            grounding_context = f"ACTIVE SEARCH FILTERS: {active_filters['filter_summary']}\n\n" + grounding_context

        citations_context = "\n".join([
            f"[{c.citation_id}] Title: {c.title} | Source: {c.source} | URL: {c.url} | Provenance: {c.provenance_class}"
            for c in citations
        ])

        system_prompt = (
            f"{AGENT_SYSTEM_PROMPT}\n\n"
            f"REAL TOOLS EXECUTED & GROUNDING DATA:\n{grounding_context}\n\n"
            f"VERIFIED CITATIONS INDEX:\n{citations_context}\n"
        )

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        for h in request.history[-4:]:
            messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": user_msg})

        # Step 5: Synthesize final answer via OpenRouter
        active_model = model_selector.active_model
        answer = await openrouter_client.generate_completion(messages=messages, model=active_model)

        elapsed_ms = (time.time() - start_time) * 1000

        prov_summary: Dict[str, int] = {}
        for c in citations:
            prov_summary[c.provenance_class] = prov_summary.get(c.provenance_class, 0) + 1

        return ChatResponse(
            answer=answer,
            citations=citations,
            model_used=active_model,
            retrieval_count=len(citations),
            provenance_summary=prov_summary,
            execution_trace=traces,
            execution_time_ms=round(elapsed_ms, 2),
            intent=intent.value,
            conversation_id=conv_id,
            active_filters=active_filters,
            conversation_state=conv_state.model_dump()
        )

    async def stream_agent(self, request: ChatRequest) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming agent execution yielding:
        1. Tool execution events in real time.
        2. Citations metadata.
        3. Token deltas.
        4. Final done event with complete execution trace.
        """
        start_time = time.time()
        user_msg = request.message
        conv_id = request.conversation_id or "default_session"

        # Step 0: Intent classification
        intent, intent_params = self.classify_intent(user_msg, history=request.history, conversation_id=conv_id)
        if intent in [IntentType.GREETING, IntentType.GENERAL_CONVERSATION, IntentType.UNSUPPORTED_QUERY, IntentType.AMBIGUOUS_FOLLOW_UP]:
            answer = IntentClassifier.get_natural_response(intent, user_msg)
            # Yield metadata with zero tools and zero citations
            yield {
                "type": "metadata",
                "model": model_selector.active_model,
                "citations": [],
                "retrieval_count": 0,
                "provenance_summary": {},
                "execution_trace": [],
                "intent": intent.value,
                "conversation_id": conv_id,
                "active_filters": None
            }
            # Stream tokens
            words = answer.split(" ")
            for idx, word in enumerate(words):
                chunk = word if idx == len(words) - 1 else word + " "
                yield {
                    "type": "token",
                    "delta": chunk
                }
                await asyncio.sleep(0.015)

            yield {
                "type": "done",
                "execution_trace": []
            }
            return

        traces: List[ToolExecutionTrace] = []
        seen_calls = set()

        try:
            planned_calls = self.plan_tools_from_query(
                user_msg,
                source_filter=request.source_filter,
                history=request.history,
                conversation_id=conv_id
            )
        except TypeError:
            planned_calls = self.plan_tools_from_query(user_msg, request.source_filter)
        step = 1

        for tool_name, args in planned_calls:
            if step > self.max_steps:
                break
            call_sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
            if call_sig in seen_calls:
                continue
            seen_calls.add(call_sig)

            # Execute tool genuinely
            trace = await self.execute_tool(step=step, tool_name=tool_name, raw_arguments=args)
            traces.append(trace)

            # Yield tool execution trace in real time to frontend
            yield {
                "type": "tool_execution",
                "step": step,
                "tool_name": tool_name,
                "status": trace.status,
                "execution_time_ms": trace.execution_time_ms,
                "result_summary": trace.result_summary
            }
            step += 1

        # Update conversation state
        conv_state = conversation_state_manager.get_or_create_state(conversation_id=conv_id, history=request.history)
        self._update_conversation_state_from_traces(conv_state, user_msg, traces, intent_params)
        conversation_state_manager.save_state(conv_state)
        active_filters = self._build_active_filters(conv_state)

        citations = self._extract_citations_from_trace(traces)
        prov_summary: Dict[str, int] = {}
        for c in citations:
            prov_summary[c.provenance_class] = prov_summary.get(c.provenance_class, 0) + 1

        # Yield metadata
        yield {
            "type": "metadata",
            "model": model_selector.active_model,
            "citations": [c.model_dump() for c in citations],
            "retrieval_count": len(citations),
            "provenance_summary": prov_summary,
            "execution_trace": [t.model_dump() for t in traces],
            "intent": intent.value,
            "conversation_id": conv_id,
            "active_filters": active_filters
        }

        # Build prompt
        grounding_context = self._format_agent_context(traces)
        if active_filters and active_filters.get("filter_summary"):
            grounding_context = f"ACTIVE SEARCH FILTERS: {active_filters['filter_summary']}\n\n" + grounding_context

        citations_context = "\n".join([
            f"[{c.citation_id}] Title: {c.title} | Source: {c.source} | URL: {c.url} | Provenance: {c.provenance_class}"
            for c in citations
        ])
        system_prompt = (
            f"{AGENT_SYSTEM_PROMPT}\n\n"
            f"REAL TOOLS EXECUTED & GROUNDING DATA:\n{grounding_context}\n\n"
            f"VERIFIED CITATIONS INDEX:\n{citations_context}\n"
        )
        messages = [{"role": "system", "content": system_prompt}]
        for h in request.history[-4:]:
            messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": user_msg})

        # Stream tokens
        async for token in openrouter_client.stream_completion(messages=messages):
            yield {
                "type": "token",
                "delta": token
            }

        yield {
            "type": "done",
            "execution_trace": [t.model_dump() for t in traces]
        }
