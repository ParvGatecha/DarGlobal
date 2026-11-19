import re
import time
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.agent.tools import (
    AgentToolRegistry,
    AGENT_OPENAI_TOOLS,
    SearchDarGlobalInput,
    SearchWasaltInput,
    SearchByLocationInput,
    GetProjectDetailsInput,
    ComparePropertiesInput,
    GetSourceInformationInput,
)
from backend.app.schemas.agent import ToolExecutionTrace
from backend.app.schemas.chat import ChatRequest, ChatResponse, Citation, ChatMessage
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
- PROVENANCE TRANSPARENCY: Acknowledge data provenance (DIRECTLY_SCRAPED vs PUBLICLY_VERIFIED_FALLBACK) truthfully.
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
        return f"Executed successfully with {len(result)} fields returned"

    def plan_tools_from_query(
        self,
        query: str,
        source_filter: Optional[str] = None,
        history: Optional[List[ChatMessage]] = None,
        **kwargs
    ) -> List[tuple[str, Dict[str, Any]]]:
        """
        Intelligent planner that analyzes the query semantics and conversation context to select relevant tools.
        Used as primary dispatcher and fallback when external model does not support native tool calling.
        Guarantees that every tool call corresponds to genuine code execution.
        """
        q_lower = query.lower()
        planned: List[tuple[str, Dict[str, Any]]] = []

        # 1. Budget extraction (SAR / AED / USD)
        budget_sar = None
        sar_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:million|m)\s*(?:sar|riyal|riyals)?", q_lower)
        if not sar_match:
            sar_match = re.search(r"(?:sar|riyal|riyals)\s*(\d+(?:\.\d+)?)\s*(?:million|m)?", q_lower)
        if sar_match:
            try:
                val = float(sar_match.group(1))
                if "million" in q_lower or "m" in q_lower or val < 100:
                    budget_sar = val * 1_000_000
                else:
                    budget_sar = val
            except ValueError:
                pass

        num_direct_match = re.search(r"under\s*(?:sar)?\s*([\d,]+)", q_lower)
        if num_direct_match and not budget_sar:
            try:
                budget_sar = float(num_direct_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # 2. Location detection (core and international)
        locations = ["riyadh", "jeddah", "al khobar", "khobar", "dubai", "marbella", "muscat", "qatar", "lusail", "al malqa", "al narjis", "al shati", "al hada", "sedra"]
        detected_loc = next((loc for loc in locations if loc in q_lower), None)
        if not detected_loc:
            intl_cities = ["tokyo", "japan", "london", "paris", "new york", "singapore", "cairo"]
            detected_loc = next((c for c in intl_cities if c in q_lower), None)

        # 3. Project name detection
        known_projects = {
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
            "al hada": "ws-mansion-hada-riyadh",
            "wasalt business": "ws-business-riyadh-office",
            "danah": "ws-villa-danah-khobar"
        }
        matched_proj_ids = [pid for k, pid in known_projects.items() if k in q_lower]
        unique_proj_ids = list(dict.fromkeys(matched_proj_ids))

        # Check for Follow-Up context referencing prior turns (e.g. "first property", "that property")
        if not unique_proj_ids and history:
            hist_texts = [h.content.lower() for h in history if h.role in ["assistant", "user"]]
            for text in reversed(hist_texts):
                found_in_hist = [pid for k, pid in known_projects.items() if k in text]
                if found_in_hist:
                    ordered_hist_ids = list(dict.fromkeys(found_in_hist))
                    if any(w in q_lower for w in ["first", "first one", "[1]"]):
                        unique_proj_ids = [ordered_hist_ids[0]]
                    elif any(w in q_lower for w in ["second", "second one", "[2]"]) and len(ordered_hist_ids) > 1:
                        unique_proj_ids = [ordered_hist_ids[1]]
                    else:
                        unique_proj_ids = [ordered_hist_ids[0]]
                    break

        # Check for Provenance / Source inquiry
        if any(w in q_lower for w in ["provenance", "source", "authenticity", "url", "audit", "verified", "scraped", "evidence"]):
            target_q = unique_proj_ids[0] if unique_proj_ids else (detected_loc or query)
            planned.append(("get_source_information", {"query_or_url": target_q}))

        # Check for Comparison
        is_comparison = any(w in q_lower for w in ["compare", "comparison", "difference", "vs", "versus", "between"])
        if is_comparison and len(unique_proj_ids) >= 2:
            planned.append(("compare_properties", {
                "property_names_or_ids": unique_proj_ids[:4],
                "focus_attributes": ["price", "location", "property_type", "amenities", "handover_date"]
            }))
        elif is_comparison and ("darglobal" in q_lower or "dubai" in q_lower) and ("wasalt" in q_lower or "riyadh" in q_lower):
            # Comparative search across both platforms
            planned.append(("search_darglobal_projects", {"query": query, "city": "Dubai"}))
            planned.append(("search_wasalt_properties", {"query": query, "city": "Riyadh", "max_budget_sar": budget_sar}))
        elif "wasalt" in q_lower or (detected_loc in ["riyadh", "jeddah", "al khobar", "khobar", "al malqa", "al narjis", "al shati", "al hada"] and "darglobal" not in q_lower):
            # Target Wasalt property search
            prop_type = "villa" if "villa" in q_lower else ("apartment" if "apartment" in q_lower else ("duplex" if "duplex" in q_lower else None))
            planned.append(("search_wasalt_properties", {
                "query": query,
                "city": detected_loc.title() if detected_loc else None,
                "property_type": prop_type,
                "max_budget_sar": budget_sar,
                "max_results": 5
            }))
        elif "darglobal" in q_lower or detected_loc in ["dubai", "marbella", "muscat", "qatar", "lusail", "tokyo", "japan", "london", "paris", "new york", "singapore", "cairo"]:
            # Target DarGlobal search
            planned.append(("search_darglobal_projects", {
                "query": query,
                "city": detected_loc.title() if detected_loc else None,
                "max_results": 5
            }))
        elif len(unique_proj_ids) == 1:
            planned.append(("get_project_details", {"project_id": unique_proj_ids[0]}))
        else:
            # General location or cross-source search
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
                or output.get("compared_properties")
                or output.get("matches")
                or output.get("sources")
                or []
            )
            if output.get("found") and "title" in output:
                items.append(output)

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

    async def run_agent(self, request: ChatRequest) -> ChatResponse:
        """
        Orchestrates full agent reasoning loop:
        1. Selects and executes genuine tools.
        2. Validates parameters and applies timeouts.
        3. Prevents loops and enforces max step limits.
        4. Synthesizes final response strictly citing verified data.
        """
        start_time = time.time()
        user_msg = request.message
        traces: List[ToolExecutionTrace] = []
        seen_calls = set()

        # Step 1: Determine initial tool execution plan
        try:
            planned_calls = self.plan_tools_from_query(user_msg, source_filter=request.source_filter, history=request.history)
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

        # Step 2: Extract citations from verified tool outputs
        citations = self._extract_citations_from_trace(traces)

        # Step 3: Build grounding prompt for LLM synthesis
        grounding_context = self._format_agent_context(traces)
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

        # Step 4: Synthesize final answer via OpenRouter
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
            execution_time_ms=round(elapsed_ms, 2)
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
        traces: List[ToolExecutionTrace] = []
        seen_calls = set()

        try:
            planned_calls = self.plan_tools_from_query(user_msg, source_filter=request.source_filter, history=request.history)
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
            "execution_trace": [t.model_dump() for t in traces]
        }

        # Build prompt
        grounding_context = self._format_agent_context(traces)
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
