import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from backend.app.retrieval.hybrid_search import HybridSearchEngine
from backend.app.llm.openrouter_client import openrouter_client
from backend.app.llm.model_selector import model_selector
from backend.app.schemas.chat import ChatRequest, ChatResponse, Citation, ChatMessage
from backend.app.core.logger import logger

SYSTEM_PROMPT_TEMPLATE = """You are "DarGlobal Intelligence", an authoritative, elite AI real estate advisor specializing in luxury branded developments by DarGlobal and prime Saudi real estate on Wasalt.

TASK & OBJECTIVE:
Provide accurate, professional, and comprehensive answers to user inquiries regarding projects, properties, locations, amenities, prices, developer partnerships, handover dates, and data provenance.

GROUNDING, INTEGRITY & PROVENANCE RULES:
1. STRICT TRUTHFULNESS: Answer strictly using ONLY the retrieved real estate context provided below.
2. NO FABRICATION: Never invent or assume property prices, unit counts, handover dates, or luxury amenities not explicitly confirmed in the context.
3. MANDATORY CITATIONS: For every factual claim, property attribute, or metric you provide, you MUST cite the relevant document number using square brackets, e.g., [1] or [1][2].
4. SOURCE TRANSPARENCY: When citing documents, maintain absolute fidelity to the stated provenance. If documents are marked as PUBLICLY_VERIFIED_FALLBACK (due to target website WAF challenges), acknowledge that the data is verified from official disclosures and sitemaps. Never claim unverified data was directly scraped.
5. UNAVAILABLE DATA & NEGATIVE QUERY GROUNDING: If the user asks about a location, property, developer, or specification that is not in the context (for example, properties in Tokyo), explicitly state: "I couldn't find verified [Location/Property] properties in the indexed dataset." NEVER claim or imply that a company does not operate in a jurisdiction or city merely because the indexed dataset has no matching records.
6. TONE: Executive, polished, factual, and informative. Use clean Markdown formatting with clear headings, bullet points, and bold metrics.

RETRIEVED CONTEXT DOCUMENTS:
{context_str}
"""

class RAGEngine:
    """
    Agentic RAG Engine with hybrid retrieval, strict provenance auditing,
    anti-hallucination guardrails, and automatic source citation attribution.
    """

    def __init__(self, retriever: HybridSearchEngine):
        self.retriever = retriever

    def _build_context_string(self, hits: List[Dict[str, Any]]) -> str:
        if not hits:
            return "No matching property records found in the database."

        context_blocks = []
        for idx, hit in enumerate(hits):
            meta = hit.get("metadata", {})
            title = meta.get("title", "Property Listing")
            source = meta.get("source", "Real Estate Source")
            url = meta.get("url", "")
            prov_class = meta.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
            ext_method = meta.get("extraction_method", "sitemap_discovery_and_public_dossier")
            notes = meta.get("origin_notes", "")
            doc_id = idx + 1

            block = (
                f"--- Document [{doc_id}] ---\n"
                f"Title: {title}\n"
                f"Source: {source} | Canonical URL: {url}\n"
                f"Provenance: {prov_class} | Method: {ext_method}\n"
                f"Audit Note: {notes}\n"
                f"Content:\n{hit['text']}\n"
            )
            context_blocks.append(block)

        return "\n".join(context_blocks)

    def _build_messages(
        self,
        query: str,
        context_str: str,
        history: List[ChatMessage]
    ) -> List[Dict[str, str]]:
        system_content = SYSTEM_PROMPT_TEMPLATE.format(context_str=context_str)
        messages = [{"role": "system", "content": system_content}]

        # Add recent conversation history (last 4 turns)
        for msg in history[-4:]:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": query})
        return messages

    async def answer_query(self, request: ChatRequest) -> ChatResponse:
        """Non-streaming conversational RAG response."""
        start_time = time.time()

        from backend.app.agent.intent import IntentClassifier, IntentType
        intent, _ = IntentClassifier.classify(request.message, history=request.history)
        if intent in [IntentType.GREETING, IntentType.GENERAL_CONVERSATION, IntentType.UNSUPPORTED_QUERY]:
            answer = IntentClassifier.get_natural_response(intent, request.message)
            elapsed_ms = (time.time() - start_time) * 1000
            return ChatResponse(
                answer=answer,
                citations=[],
                model_used=model_selector.active_model,
                retrieval_count=0,
                provenance_summary={},
                execution_time_ms=round(elapsed_ms, 2),
                intent=intent.value
            )

        # Step 1: Hybrid retrieval (Dense + BM25 with RRF)
        hits = self.retriever.search(
            query=request.message,
            k_results=request.top_k or 5,
            source_filter=request.source_filter
        )
        citations = self.retriever.format_citations(hits)
        context_str = self._build_context_string(hits)

        # Step 2: Assemble messages
        messages = self._build_messages(request.message, context_str, request.history)

        # Step 3: Query LLM
        active_model = model_selector.active_model
        answer = await openrouter_client.generate_completion(messages=messages, model=active_model)

        elapsed_ms = (time.time() - start_time) * 1000

        # Provenance summary calculation
        prov_summary: Dict[str, int] = {}
        for c in citations:
            prov_summary[c.provenance_class] = prov_summary.get(c.provenance_class, 0) + 1

        return ChatResponse(
            answer=answer,
            citations=citations,
            model_used=active_model,
            retrieval_count=len(hits),
            provenance_summary=prov_summary,
            execution_time_ms=round(elapsed_ms, 2)
        )

    async def stream_query(self, request: ChatRequest) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming conversational RAG response yielding tokens and citations."""
        from backend.app.agent.intent import IntentClassifier, IntentType
        import asyncio
        intent, _ = IntentClassifier.classify(request.message, history=request.history)
        if intent in [IntentType.GREETING, IntentType.GENERAL_CONVERSATION, IntentType.UNSUPPORTED_QUERY]:
            answer = IntentClassifier.get_natural_response(intent, request.message)
            yield {
                "type": "metadata",
                "model": model_selector.active_model,
                "citations": [],
                "retrieval_count": 0,
                "provenance_summary": {}
            }
            words = answer.split(" ")
            for idx, word in enumerate(words):
                chunk = word if idx == len(words) - 1 else word + " "
                yield {
                    "type": "token",
                    "delta": chunk
                }
                await asyncio.sleep(0.015)
            yield {
                "type": "done"
            }
            return

        # Step 1: Hybrid retrieval
        hits = self.retriever.search(
            query=request.message,
            k_results=request.top_k or 5,
            source_filter=request.source_filter
        )
        citations = self.retriever.format_citations(hits)
        context_str = self._build_context_string(hits)

        prov_summary: Dict[str, int] = {}
        for c in citations:
            prov_summary[c.provenance_class] = prov_summary.get(c.provenance_class, 0) + 1

        # First yield citations and provenance metadata
        yield {
            "type": "metadata",
            "model": model_selector.active_model,
            "citations": [c.model_dump() for c in citations],
            "retrieval_count": len(hits),
            "provenance_summary": prov_summary
        }

        # Step 2: Assemble messages
        messages = self._build_messages(request.message, context_str, request.history)

        # Step 3: Stream tokens
        async for token in openrouter_client.stream_completion(messages=messages):
            yield {
                "type": "token",
                "delta": token
            }

        yield {
            "type": "done"
        }
