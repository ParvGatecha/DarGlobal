# DarGlobal Intelligence — Project Structure

```
DarGlobal/
├── ARCHITECTURE.md                  # Comprehensive architectural specification
├── IMPLEMENTATION_PLAN.md           # Step-by-step implementation milestones
├── PROJECT_STRUCTURE.md             # Complete repository tree and component descriptions
├── README.md                        # Master project documentation, setup, and deployment guide
├── docker-compose.yml               # Multi-container orchestration (Backend + Frontend + Storage)
├── .env.example                     # Environment variables template
│
├── backend/                         # FastAPI Python Backend Service
│   ├── Dockerfile                   # Production container definition
│   ├── requirements.txt             # Backend dependencies (FastAPI, ChromaDB, Rank-BM25, etc.)
│   ├── main.py                      # Application entry point and lifespan management
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── core/                    # Core configuration and logging
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Pydantic v2 application settings
│   │   │   └── logger.py            # Structured logging setup
│   │   │
│   │   ├── schemas/                 # Pydantic data schemas
│   │   │   ├── __init__.py
│   │   │   ├── chat.py              # ChatRequest, ChatResponse, Citation, SourceDoc
│   │   │   ├── property.py          # PropertyItem, ProjectItem, IngestionReport
│   │   │   └── health.py            # HealthStatus, ModelInfo
│   │   │
│   │   ├── ingestion/               # Scraping, parsing & data preparation
│   │   │   ├── __init__.py
│   │   │   ├── crawler.py           # Sitemap discovery & ethical crawler
│   │   │   ├── seed_data.py         # Authoritative DarGlobal & Wasalt dataset
│   │   │   ├── chunker.py           # Semantic markdown & metadata chunker
│   │   │   └── pipeline.py          # End-to-end ingestion pipeline
│   │   │
│   │   ├── retrieval/               # Hybrid search engine
│   │   │   ├── __init__.py
│   │   │   ├── vector_store.py      # ChromaDB dense vector indexing
│   │   │   ├── bm25_store.py        # Rank-BM25 keyword search index
│   │   │   └── hybrid_search.py     # Reciprocal Rank Fusion (RRF) ranker
│   │   │
│   │   ├── llm/                     # OpenRouter & RAG agent
│   │   │   ├── __init__.py
│   │   │   ├── openrouter_client.py # Dynamic OpenRouter API client with free model selector
│   │   │   ├── model_selector.py    # Auto-discovery & fallback logic for :free models
│   │   │   └── rag_engine.py        # Strict grounding, citation injector & synthesizer
│   │   │
│   │   └── api/                     # REST & SSE API routes
│   │       ├── __init__.py
│   │       └── v1/
│   │           ├── __init__.py
│   │           ├── chat.py          # /api/v1/chat & /api/v1/chat/stream
│   │           ├── properties.py    # /api/v1/properties & /api/v1/projects
│   │           ├── ingest.py        # /api/v1/ingest/trigger & status
│   │           └── health.py        # /api/v1/health & model capabilities
│   │
│   └── tests/                       # Automated backend tests
│       ├── __init__.py
│       ├── test_crawler.py          # Test crawler & sitemap parsing
│       ├── test_retrieval.py        # Test hybrid search & RRF ranking
│       └── test_rag.py              # Test RAG grounding & citations
│
├── frontend/                        # Next.js 14 TypeScript Frontend
│   ├── Dockerfile                   # Multi-stage production container build
│   ├── package.json                 # Node dependencies (Next, Tailwind, Lucide, etc.)
│   ├── tsconfig.json                # TypeScript compiler config
│   ├── tailwind.config.ts           # Tailwind CSS configuration
│   ├── next.config.mjs              # Next.js configuration
│   │
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx           # Global root layout with theme & font
│   │   │   ├── page.tsx             # Main dashboard (Chat + Explorer + Metrics)
│   │   │   └── globals.css          # Design tokens & styling
│   │   │
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx    # Conversational RAG interface with streaming
│   │   │   ├── MessageList.tsx      # Chat bubbles with markdown & inline citations
│   │   │   ├── CitationDrawer.tsx   # Side sheet inspecting source documents
│   │   │   ├── PropertyCard.tsx     # Rich preview cards for DarGlobal & Wasalt properties
│   │   │   ├── PropertyExplorer.tsx # Tabbed catalog explorer with search & filter
│   │   │   ├── SystemHeader.tsx     # Navigation bar with active model badge & status
│   │   │   └── QuickPrompts.tsx     # Real estate suggested prompt chips
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts               # Backend API client with streaming SSE support
│   │   │   ├── types.ts             # TypeScript interfaces matching backend schemas
│   │   │   └── utils.ts             # Tailwind class merging & formatting utilities
│   │   │
│   │   └── hooks/
│   │       └── useChatStream.ts     # Custom hook for SSE streaming chat
│   │
│   └── public/                      # Static brand assets
│
└── data/                            # Persistent data storage (volume mounted)
    ├── chroma_db/                   # ChromaDB vector collection files
    ├── bm25_index.pkl               # Serialized BM25 index & corpus
    ├── raw_scraped/                 # Ingested raw documents & sitemaps
    └── seed/                        # Authoritative real estate knowledge records
```
