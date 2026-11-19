import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.schemas.chat import ChatRequest, ChatMessage
from backend.app.schemas.agent import IntentType
from backend.app.agent.conversation_state import (
    ConversationStateManager,
    ConversationState,
    extract_budget_numeric,
    extract_bedrooms_count,
    extract_property_type_name,
)
from backend.app.agent.intent import IntentClassifier, AMBIGUOUS_BUDGET_RESPONSE


@pytest.fixture
def test_client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def state_manager():
    return ConversationStateManager()


def test_budget_extraction():
    assert extract_budget_numeric("under 2000000") == 2000000.0
    assert extract_budget_numeric("under 2 million") == 2000000.0
    assert extract_budget_numeric("under 2m") == 2000000.0
    assert extract_budget_numeric("below 3.5m") == 3500000.0
    assert extract_budget_numeric("max 3,000,000") == 3000000.0
    assert extract_budget_numeric("2000000") == 2000000.0
    assert extract_budget_numeric("hello world") is None


def test_bedroom_extraction():
    assert extract_bedrooms_count("two bedrooms") == 2
    assert extract_bedrooms_count("2 bedrooms") == 2
    assert extract_bedrooms_count("3 br") == 3
    assert extract_bedrooms_count("4 bed") == 4
    assert extract_bedrooms_count("luxury villa") is None


def test_property_type_extraction():
    assert extract_property_type_name("luxury villa in riyadh") == "villa"
    assert extract_property_type_name("modern apartment") == "apartment"
    assert extract_property_type_name("spacious duplex") == "duplex"
    assert extract_property_type_name("commercial office") == "commercial"


# TEST 1: Dubai -> Under 2000000 -> Urban Oasis & DG1 Living from previous results
def test_conversation_sequence_1_dubai_budget_refinement(test_client):
    orchestrator = test_client.app.state.agent_orchestrator
    conv_id = "test_seq_1"

    # Turn 1: Dubai search
    req1 = ChatRequest(
        message="I want to see properties in Dubai.",
        conversation_id=conv_id
    )
    resp1 = test_client.post("/api/v1/chat", json=req1.model_dump())
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["citations"]) >= 2
    # Verify citations are DarGlobal Dubai properties
    sources1 = [c["source"] for c in data1["citations"]]
    assert all("DarGlobal" in s for s in sources1)

    # Turn 2: Follow-up "Under 2000000"
    req2 = ChatRequest(
        message="Under 2000000",
        conversation_id=conv_id,
        history=[
            ChatMessage(role="user", content="I want to see properties in Dubai."),
            ChatMessage(role="assistant", content=data1["answer"])
        ]
    )
    resp2 = test_client.post("/api/v1/chat", json=req2.model_dump())
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Must retain Dubai, AED, and DarGlobal
    assert data2["active_filters"] is not None
    assert data2["active_filters"]["location"] == "Dubai"
    assert data2["active_filters"]["currency"] == "AED"
    assert data2["active_filters"]["budget_max"] == 2000000.0
    assert "darglobal" in data2["active_filters"]["data_sources"]

    # Filtered results should contain Urban Oasis (AED 1.25M) and DG1 Living (AED 1.4M)
    citation_titles = [c["title"].lower() for c in data2["citations"]]
    assert any("urban oasis" in t for t in citation_titles)
    assert any("dg1" in t for t in citation_titles)
    # DaVinci Tower (AED 7.5M) and W Residences (AED 2.1M) must be filtered out
    assert not any("davinci" in t for t in citation_titles)
    assert not any("w residences" in t for t in citation_titles)


# TEST 2: Riyadh -> Under 3 million -> Riyadh and SAR preserved
def test_conversation_sequence_2_riyadh_budget_refinement(test_client):
    conv_id = "test_seq_2"

    # Turn 1: Riyadh search
    req1 = ChatRequest(
        message="Find properties in Riyadh.",
        conversation_id=conv_id
    )
    resp1 = test_client.post("/api/v1/chat", json=req1.model_dump())
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["citations"]) >= 1
    assert any("Wasalt" in c["source"] or "DarGlobal" in c["source"] for c in data1["citations"])

    # Turn 2: "Under 3 million"
    req2 = ChatRequest(
        message="Under 3 million",
        conversation_id=conv_id,
        history=[
            ChatMessage(role="user", content="Find properties in Riyadh."),
            ChatMessage(role="assistant", content=data1["answer"])
        ]
    )
    resp2 = test_client.post("/api/v1/chat", json=req2.model_dump())
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["active_filters"] is not None
    assert data2["active_filters"]["location"] == "Riyadh"
    assert data2["active_filters"]["currency"] == "SAR"
    assert data2["active_filters"]["budget_max"] == 3000000.0
    # Must NOT switch to AED or Dubai
    assert data2["active_filters"]["currency"] != "AED"


# TEST 3: Dubai apartments -> Two bedrooms -> Dubai preserved, bedrooms updated
def test_conversation_sequence_3_bedroom_refinement(test_client):
    conv_id = "test_seq_3"

    # Turn 1: Dubai apartments
    req1 = ChatRequest(
        message="Show me apartments in Dubai.",
        conversation_id=conv_id
    )
    resp1 = test_client.post("/api/v1/chat", json=req1.model_dump())
    assert resp1.status_code == 200

    # Turn 2: Two bedrooms
    req2 = ChatRequest(
        message="Two bedrooms",
        conversation_id=conv_id,
        history=[
            ChatMessage(role="user", content="Show me apartments in Dubai."),
            ChatMessage(role="assistant", content="Here are apartments in Dubai.")
        ]
    )
    resp2 = test_client.post("/api/v1/chat", json=req2.model_dump())
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["active_filters"] is not None
    assert data2["active_filters"]["location"] == "Dubai"
    assert data2["active_filters"]["bedrooms"] == 2


# TEST 4: Dubai -> What about Riyadh? -> Location changes, currency changes to SAR
def test_conversation_sequence_4_location_switch(test_client):
    conv_id = "test_seq_4"

    # Turn 1: Dubai
    req1 = ChatRequest(
        message="I want to see properties in Dubai.",
        conversation_id=conv_id
    )
    resp1 = test_client.post("/api/v1/chat", json=req1.model_dump())
    assert resp1.status_code == 200

    # Turn 2: What about Riyadh?
    req2 = ChatRequest(
        message="What about Riyadh?",
        conversation_id=conv_id,
        history=[
            ChatMessage(role="user", content="I want to see properties in Dubai."),
            ChatMessage(role="assistant", content="Here are Dubai properties.")
        ]
    )
    resp2 = test_client.post("/api/v1/chat", json=req2.model_dump())
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["active_filters"] is not None
    assert data2["active_filters"]["location"] == "Riyadh"
    assert data2["active_filters"]["currency"] == "SAR"
    assert "wasalt" in data2["active_filters"]["data_sources"]


# TEST 5: Compare properties in Dubai and Riyadh -> Both sources searched
def test_conversation_sequence_5_compare_cross_market(test_client):
    conv_id = "test_seq_5"

    req = ChatRequest(
        message="Compare properties in Dubai and Riyadh.",
        conversation_id=conv_id
    )
    resp = test_client.post("/api/v1/chat", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()

    # Intent is PROPERTY_COMPARISON
    assert data["intent"] == IntentType.PROPERTY_COMPARISON.value
    # Executed tools should include comparison or searches for both platforms
    traces = data["execution_trace"]
    tool_names = [t["tool_name"] for t in traces]
    assert any(t in ["compare_properties", "search_darglobal_projects", "search_wasalt_properties"] for t in tool_names)


# TEST 6: Riyadh villas -> Actually, show me Dubai apartments -> Overrides previous state
def test_conversation_sequence_6_explicit_override(test_client):
    conv_id = "test_seq_6"

    # Turn 1: Riyadh villas
    req1 = ChatRequest(
        message="Show me villas in Riyadh.",
        conversation_id=conv_id
    )
    resp1 = test_client.post("/api/v1/chat", json=req1.model_dump())
    assert resp1.status_code == 200

    # Turn 2: Actually, show me Dubai apartments
    req2 = ChatRequest(
        message="Actually, show me Dubai apartments.",
        conversation_id=conv_id,
        history=[
            ChatMessage(role="user", content="Show me villas in Riyadh."),
            ChatMessage(role="assistant", content="Here are villas in Riyadh.")
        ]
    )
    resp2 = test_client.post("/api/v1/chat", json=req2.model_dump())
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["active_filters"] is not None
    assert data2["active_filters"]["location"] == "Dubai"
    assert data2["active_filters"]["currency"] == "AED"
    assert data2["active_filters"]["property_type"] == "apartment"
    assert "darglobal" in data2["active_filters"]["data_sources"]


# TEST 7: Dubai -> Under 2 million -> Show me the second one -> Resolves DG1 Living Dubai
def test_conversation_sequence_7_referential_details(test_client):
    conv_id = "test_seq_7"

    # Turn 1: Dubai
    req1 = ChatRequest(message="I want to see properties in Dubai.", conversation_id=conv_id)
    resp1 = test_client.post("/api/v1/chat", json=req1.model_dump())
    assert resp1.status_code == 200

    # Turn 2: Under 2000000
    req2 = ChatRequest(
        message="Under 2000000",
        conversation_id=conv_id,
        history=[
            ChatMessage(role="user", content="I want to see properties in Dubai."),
            ChatMessage(role="assistant", content=resp1.json()["answer"])
        ]
    )
    resp2 = test_client.post("/api/v1/chat", json=req2.model_dump())
    assert resp2.status_code == 200

    # Turn 3: Show me the second one
    req3 = ChatRequest(
        message="Show me the second one",
        conversation_id=conv_id,
        history=[
            ChatMessage(role="user", content="I want to see properties in Dubai."),
            ChatMessage(role="assistant", content=resp1.json()["answer"]),
            ChatMessage(role="user", content="Under 2000000"),
            ChatMessage(role="assistant", content=resp2.json()["answer"]),
        ]
    )
    resp3 = test_client.post("/api/v1/chat", json=req3.model_dump())
    assert resp3.status_code == 200
    data3 = resp3.json()

    # The second filtered Dubai property is DG1 Living Dubai (dg-dg1-living)
    # The tool executed should be get_project_details for dg-dg1-living
    traces3 = data3["execution_trace"]
    assert any(
        t["tool_name"] == "get_project_details" and t["arguments"].get("project_id") == "dg-dg1-living"
        for t in traces3
    )
    assert any("dg1" in c["title"].lower() for c in data3["citations"])


# TEST 8: Under 2 million (no context) -> Asks user for location and currency
def test_conversation_sequence_8_ambiguous_budget_no_context(test_client):
    conv_id = "test_seq_8_fresh"

    req = ChatRequest(
        message="Under 2 million.",
        conversation_id=conv_id,
        history=[]
    )
    resp = test_client.post("/api/v1/chat", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()

    # Must classify as AMBIGUOUS_FOLLOW_UP and NOT execute any retrieval tools
    assert data["intent"] == IntentType.AMBIGUOUS_FOLLOW_UP.value
    assert len(data["execution_trace"]) == 0
    assert len(data["citations"]) == 0

    # The response must ask the user for location and currency
    answer_lower = data["answer"].lower()
    assert "location and currency" in answer_lower or "specify your target city or currency" in answer_lower
    assert "dubai" in answer_lower and "riyadh" in answer_lower
