# DarGlobal Intelligence — Implementation Plan

## Phase 1: Environment & Foundational Architecture (Completed)
- [x] Inspect `https://www.darglobal.co.uk/` and `https://wasalt.sa/` live structures, headers, and security gates.
- [x] Verify robots.txt and sitemap availability (`darglobal.co.uk/sitemap.xml`, `cdn.wasalt.sa/sitemap/`).
- [x] Identify WAF/bot mitigation mechanisms (Imperva Incapsula hCaptcha on DarGlobal, Cloudflare Turnstile on Wasalt).
- [x] Query OpenRouter `/api/v1/models` to discover active `:free` tier models.
- [x] Author comprehensive `ARCHITECTURE.md`.
- [x] Author `IMPLEMENTATION_PLAN.md`.
- [x] Author `PROJECT_STRUCTURE.md`.

---

## Phase 2: Ingestion & Knowledge Preprocessing Engine
- [ ] Implement `backend/app/ingestion/crawler.py`:
  - Sitemap discovery and crawler for DarGlobal and Wasalt.
  - Ethical rate-limited HTTP/Playwright fetcher with challenge detection (`_Incapsula_Resource`, `hcaptcha`, `challenges.cloudflare.com`).
  - Safe error handling that flags protected pages rather than attempting unauthorized CAPTCHA bypass.
- [ ] Implement `backend/app/ingestion/seed_data.py`:
  - High-fidelity structured datasets for DarGlobal flagship branded projects (Pagani, Missoni, Lamborghini, Aston Martin, Elie Saab, Trump International across UAE, Oman, Qatar, Spain, UK, KSA).
  - High-fidelity structured datasets for Wasalt key market listings, district benchmarks, and real estate communities (Riyadh, Jeddah, Al Khobar, Dammam).
- [ ] Implement `backend/app/ingestion/chunker.py`:
  - Semantic sliding chunker preserving document hierarchy, metadata tags, developer, location, property type, price, amenities, and source URL.
- [ ] Implement `backend/app/ingestion/pipeline.py`:
  - End-to-end ingestion orchestrator that coordinates crawling, seed datasets, chunking, and index persistence.

---

## Phase 3: Hybrid Retrieval & Vector Database (ChromaDB + BM25)
- [ ] Implement `backend/app/retrieval/vector_store.py`:
  - ChromaDB persistent vector database with embedding generator (sentence-transformers / local embedding fallback).
- [ ] Implement `backend/app/retrieval/bm25_store.py`:
  - Fast lexical search engine using Rank-BM25 with tokenization tuned for real estate keywords and brand names.
- [ ] Implement `backend/app/retrieval/hybrid_search.py`:
  - Reciprocal Rank Fusion (RRF) algorithm combining dense vector similarity scores and sparse BM25 scores.
  - Source metadata and citation extraction logic.

---

## Phase 4: OpenRouter LLM Integration & Agentic RAG
- [ ] Implement `backend/app/llm/model_selector.py`:
  - Dynamic discovery of active `:free` models from OpenRouter API.
  - Environment variable overrides (`OPENROUTER_MODEL`).
  - Graceful fallback sequence across free models.
- [ ] Implement `backend/app/llm/rag_chain.py`:
  - Strict anti-hallucination prompt templates enforcing ground-truth retrieval.
  - Automatic inline citation generation `[1]`, `[2]`.
  - Source citation mapping and confidence scoring.
  - Fallback responses for queries without available data.

---

## Phase 5: FastAPI Backend Service
- [ ] Implement `backend/app/core/config.py`: Pydantic settings loading from `.env`.
- [ ] Implement `backend/app/schemas/chat.py`: Pydantic models for queries, responses, sources, citations.
- [ ] Implement `backend/app/api/endpoints/chat.py`: Standard and Server-Sent Events (SSE) streaming chat endpoints.
- [ ] Implement `backend/app/api/endpoints/ingest.py`: Admin/pipeline trigger and status endpoints.
- [ ] Implement `backend/app/api/endpoints/health.py`: System health, vector count, and active model reporting.
- [ ] Implement `backend/main.py`: FastAPI application setup with CORS middleware and lifecycle handlers.

---

## Phase 6: Modern Next.js Frontend
- [ ] Scaffold Next.js 14 App Router project with TypeScript and Tailwind CSS.
- [ ] Install Lucide icons and UI components.
- [ ] Implement Real Estate Chat Assistant:
  - Streaming conversational message interface.
  - Formatted Markdown rendering with syntax highlighting.
  - Interactive citation badges linking directly to source URLs.
- [ ] Implement Interactive Side Drawer / Property Explorer:
  - Visual property cards with developer badges, price, location, and amenities tags.
- [ ] Implement Suggested Inquiry Chips & Filter Controls (DarGlobal vs. Wasalt).

---

## Phase 7: Containerization & Deployment
- [ ] Write `backend/Dockerfile` with Python 3.12/3.13, dependencies, and persistent volume support.
- [ ] Write `frontend/Dockerfile` multi-stage build for Next.js.
- [ ] Write `docker-compose.yml` orchestrating both services with named volume `darglobal-data`.
- [ ] Write `.env.example` and configuration documentation.
- [ ] Create automated test suite verifying crawler, hybrid retriever, RRF, and chat endpoints.
- [ ] Prepare public deployment configurations (Render, Railway, Hugging Face Spaces, or Cloud VPS).
- [ ] Verify end-to-end functionality and provide working instructions.
