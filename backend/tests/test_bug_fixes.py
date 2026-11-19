import pytest
import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.agent.intent import IntentClassifier, IntentType
from backend.app.agent.orchestrator import AgentOrchestrator
from backend.app.agent.tools import AgentToolRegistry
from backend.app.retrieval.hybrid_search import HybridSearchEngine
from backend.app.retrieval.vector_store import VectorStore
from backend.app.retrieval.bm25_store import BM25Store
from backend.app.schemas.chat import ChatRequest, ChatMessage
from backend.app.ingestion.seed_data import (
    is_allowed_property_result,
    get_all_properties_only,
    get_all_indexed_items,
    ALLOWED_PROPERTY_RESULT_TYPES,
    EXCLUDED_DOCUMENT_TYPES,
)

client = TestClient(app)

@pytest.fixture(scope="module")
def agent_orchestrator():
    vector_store = VectorStore()
    bm25_store = BM25Store()
    retriever = HybridSearchEngine(vector_store=vector_store, bm25_store=bm25_store)
    registry = AgentToolRegistry(retriever=retriever)
    return AgentOrchestrator(tool_registry=registry)


# ============================================================================
# BUG 1 REGRESSION: GREETING VS DUBAI SEARCH
# ============================================================================

@pytest.mark.asyncio
async def test_regression_greeting_zero_tools(agent_orchestrator):
    """Bug 1 & 5: Greeting queries must return a welcoming response with 0 tools executed."""
    request = ChatRequest(message="hi", history=[])
    response = await agent_orchestrator.run_agent(request)

    assert response.intent == IntentType.GREETING.value
    assert len(response.execution_trace) == 0
    assert response.retrieval_count == 0
    assert "Welcome to DarGlobal Intelligence" in response.answer
    assert "explore" in response.answer.lower()


@pytest.mark.asyncio
async def test_regression_dubai_search_not_greeting_with_history(agent_orchestrator):
    """
    Bug 1 & 5: When user asks to explore properties in Dubai after a greeting in history,
    the chatbot must NOT return the canned greeting. It must execute retrieval tools
    and return actual Dubai properties.
    """
    history = [
        ChatMessage(role="user", content="hi"),
        ChatMessage(role="assistant", content="Hello! Welcome to DarGlobal Intelligence. How can I help?"),
    ]
    request = ChatRequest(message="I would like to explore properties in dubai", history=history)
    response = await agent_orchestrator.run_agent(request)

    # Must NOT be classified as greeting
    assert response.intent != IntentType.GREETING.value
    # Tools must have executed
    assert len(response.execution_trace) > 0
    assert any(t.status == "SUCCESS" for t in response.execution_trace)
    # Citations must be populated
    assert response.retrieval_count > 0

    # Answer must NOT be the canned greeting
    assert "Hello! Welcome to DarGlobal Intelligence" not in response.answer
    # Answer must contain verified Dubai properties
    answer_lower = response.answer.lower()
    assert any(proj in answer_lower for proj in ["davinci", "pagani", "urban oasis", "missoni", "dg1", "w residences"])
    # Answer must include an engaging closing prompt (Bug 4)
    assert any(phrase in answer_lower for phrase in ["would you like to", "explore", "compare", "amenities"])


# ============================================================================
# BUG 2 REGRESSION: SITEMAP DOCUMENTS NEVER RETURNED AS PROPERTY CARDS
# ============================================================================

def test_regression_sitemaps_excluded_from_properties_endpoint():
    """Bug 2 & 5: Sitemaps must NEVER be returned in GET /api/v1/properties by default."""
    resp = client.get("/api/v1/properties")
    assert resp.status_code == 200
    properties = resp.json()
    assert len(properties) >= 14

    for prop in properties:
        assert "sitemap" not in prop["id"].lower()
        assert "sitemap" not in prop["title"].lower()
        assert "sitemap" not in prop["property_type"].lower()
        assert prop.get("result_type") in ALLOWED_PROPERTY_RESULT_TYPES


def test_regression_sitemaps_filtered_from_location_and_project_tools(agent_orchestrator):
    """Bug 2 & 5: search_by_location and search_darglobal_projects must NEVER return sitemaps."""
    from backend.app.schemas.agent import SearchByLocationInput, SearchDarGlobalInput

    # 1. Location search for Dubai
    loc_res = agent_orchestrator.tools.search_by_location(
        SearchByLocationInput(location="Dubai", max_results=10)
    )
    for m in loc_res["matches"]:
        assert "sitemap" not in m["id"].lower()
        assert "sitemap" not in m["title"].lower()
        assert "sitemap" not in m["property_type"].lower()

    # 2. DarGlobal project search
    dg_res = agent_orchestrator.tools.search_darglobal_projects(
        SearchDarGlobalInput(query="Dubai luxury developments", city="Dubai", max_results=10)
    )
    for p in dg_res["projects"]:
        assert "sitemap" not in p["id"].lower()
        assert "sitemap" not in p["title"].lower()
        assert "sitemap" not in p["property_type"].lower()


def test_regression_is_allowed_property_result_predicate():
    """Bug 2 & 5: Unit test for strict filtering predicate."""
    sitemap_item = {
        "id": "dg-sitemap-index-scraped",
        "title": "DarGlobal Canonical Sitemap Index (476 URLs)",
        "property_type": "Canonical XML Sitemap Index",
        "result_type": "XML_SITEMAP",
    }
    assert is_allowed_property_result(sitemap_item) is False

    valid_property = {
        "id": "dg-pagani-geometria",
        "title": "DaVinci Tower by Pagani",
        "property_type": "Ultra-Luxury Apartments & Penthouses",
        "result_type": "REAL_ESTATE_PROJECT",
    }
    assert is_allowed_property_result(valid_property) is True


# ============================================================================
# BUG 3 REGRESSION: PROVENANCE TRANSPARENCY
# ============================================================================

@pytest.mark.asyncio
async def test_regression_provenance_labels(agent_orchestrator):
    """Bug 3 & 5: Provenance must clearly distinguish Fallback from Directly Scraped without contradictory labels."""
    request = ChatRequest(message="What luxury developments does DarGlobal offer in Dubai?")
    response = await agent_orchestrator.run_agent(request)

    # Check citations provenance
    for citation in response.citations:
        assert citation.provenance_class in ["PUBLICLY_VERIFIED_FALLBACK", "DIRECTLY_SCRAPED"]
        if citation.provenance_class == "PUBLICLY_VERIFIED_FALLBACK":
            assert citation.is_directly_scraped is False
            assert citation.url.startswith("https://")

    # In response answer, check that fallback records are labeled accurately
    assert "DarGlobal Verified" not in response.answer  # Misleading header eliminated


# ============================================================================
# BUG 4 REGRESSION: FINAL RESPONSE QUALITY (ENGAGING OPENING, CARDS, CLOSING)
# ============================================================================

@pytest.mark.asyncio
async def test_regression_response_quality_structure(agent_orchestrator):
    """Bug 4 & 5: Response must include engaging opening, numbered items with specs/links, and closing prompt."""
    request = ChatRequest(message="I would like to explore properties in dubai")
    response = await agent_orchestrator.run_agent(request)

    answer = response.answer
    # 1. Opening overview
    assert "DarGlobal" in answer
    assert "Dubai" in answer
    # 2. Numbered highlights
    assert "#### 1." in answer or "#### [1]" in answer
    assert "- **Developer" in answer or "- **Location" in answer
    assert "- **Property Type" in answer
    # 3. Source & Provenance link
    assert "http" in answer or "Publicly Verified Fallback" in answer
    # 4. Engaging closing prompt
    assert "?" in answer
    assert any(term in answer.lower() for term in ["explore", "compare", "amenities", "budget", "layout"])


# ============================================================================
# BUG 5: EMPTY SEARCH RESULTS & HONEST EXPLANATION (TOKYO)
# ============================================================================

@pytest.mark.asyncio
async def test_regression_unindexed_location_tokyo(agent_orchestrator):
    """Bug 5: Searching for Tokyo must return an honest explanation scoped to the indexed dataset."""
    request = ChatRequest(message="What properties does DarGlobal offer in Tokyo?")
    response = await agent_orchestrator.run_agent(request)

    answer = response.answer
    assert "couldn't find verified Tokyo properties in the indexed dataset" in answer or "indexed dataset" in answer
    # Must never claim that the company does not operate globally
    assert "does not operate" not in answer.lower()
    # Must state indexed coverage
    assert "Dubai" in answer
    assert "Oman" in answer or "Muscat" in answer


# ============================================================================
# BUG 5: FOLLOW-UP QUESTIONS & CONTEXT RESOLUTION
# ============================================================================

@pytest.mark.asyncio
async def test_regression_followup_question_amenities(agent_orchestrator):
    """Bug 5: Follow-up question referencing 'the first property' must resolve context and extract amenities."""
    history = [
        ChatMessage(role="user", content="What luxury developments does DarGlobal offer in Dubai?"),
        ChatMessage(
            role="assistant",
            content="DarGlobal offers several premier developments: 1. DaVinci Tower by Pagani located in Downtown Dubai. 2. Urban Oasis by Missoni in Business Bay."
        )
    ]
    request = ChatRequest(message="What amenities does the first property offer?", history=history)
    response = await agent_orchestrator.run_agent(request)

    # Must resolve to DaVinci Tower / Pagani
    assert any(t.tool_name == "get_project_details" for t in response.execution_trace)
    trace = next(t for t in response.execution_trace if t.tool_name == "get_project_details")
    assert "pagani" in str(trace.arguments.get("project_id", "")).lower()

    # Answer must detail Pagani amenities
    answer_lower = response.answer.lower()
    assert any(am in answer_lower for am in ["pagani", "carbon-fiber", "infinity", "burj khalifa", "concierge", "elevator"])


# ============================================================================
# BUG 5: REST AND SSE ENDPOINTS E2E
# ============================================================================

def test_regression_rest_endpoint_chat():
    """Bug 5: REST endpoint POST /api/v1/chat verification."""
    payload = {
        "message": "I would like to explore properties in dubai",
        "history": []
    }
    with TestClient(app) as tc:
        resp = tc.post("/api/v1/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] != "GREETING"
        assert len(data["execution_trace"]) > 0
        assert "Hello! Welcome to DarGlobal Intelligence" not in data["answer"]
        assert "Dubai" in data["answer"]


def test_regression_sse_stream_greeting():
    """Bug 5: SSE endpoint stream for greeting yields 0 tools and immediate done."""
    payload = {
        "message": "hello",
        "history": []
    }
    with TestClient(app) as tc:
        with tc.stream("POST", "/api/v1/chat/stream", json=payload) as resp:
            assert resp.status_code == 200
            events = []
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

            event_types = [e.get("type") for e in events]
            assert "metadata" in event_types
            assert "token" in event_types
            assert "done" in event_types
            assert "tool_execution" not in event_types  # Zero tools for greeting!

            meta = next(e for e in events if e.get("type") == "metadata")
            assert meta["intent"] == "GREETING"
            assert len(meta["execution_trace"]) == 0


def test_regression_sse_stream_dubai_search():
    """Bug 5: SSE endpoint stream for Dubai query yields tool execution and property tokens."""
    payload = {
        "message": "I would like to explore properties in dubai",
        "history": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hello! Welcome to DarGlobal Intelligence. How can I help?"}
        ]
    }
    with TestClient(app) as tc:
        with tc.stream("POST", "/api/v1/chat/stream", json=payload) as resp:
            assert resp.status_code == 200
            events = []
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

            event_types = [e.get("type") for e in events]
            assert "metadata" in event_types
            assert "tool_execution" in event_types  # Real tool execution event!
            assert "token" in event_types
            assert "done" in event_types

            tokens = "".join(e.get("delta", "") for e in events if e.get("type") == "token")
            assert "Hello! Welcome to DarGlobal Intelligence" not in tokens
            assert "Dubai" in tokens
