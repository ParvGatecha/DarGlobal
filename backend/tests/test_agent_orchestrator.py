import pytest
import asyncio
from backend.app.retrieval.vector_store import VectorStore
from backend.app.retrieval.bm25_store import BM25Store
from backend.app.retrieval.hybrid_search import HybridSearchEngine
from backend.app.ingestion.seed_data import get_all_indexed_items
from backend.app.ingestion.chunker import SemanticChunker
from backend.app.agent.tools import AgentToolRegistry
from backend.app.agent.orchestrator import AgentOrchestrator
from backend.app.schemas.chat import ChatRequest, ChatMessage
from backend.app.schemas.agent import IntentType

@pytest.fixture(scope="module")
def orchestrator():
    v_store = VectorStore(persist_directory="./data/test_orch_chroma")
    b_store = BM25Store(index_path="./data/test_orch_bm25.pkl")
    chunker = SemanticChunker()

    all_chunks = []
    for item in get_all_indexed_items():
        all_chunks.extend(chunker.chunk_property(item))

    v_store.add_chunks(all_chunks)
    b_store.index_chunks(all_chunks)
    retriever = HybridSearchEngine(vector_store=v_store, bm25_store=b_store)
    tools = AgentToolRegistry(retriever=retriever)
    return AgentOrchestrator(tool_registry=tools, max_steps=4, per_tool_timeout=5.0)

def test_plan_budget_query(orchestrator):
    # Example 1: Find luxury properties in Riyadh under SAR 2 million
    query = "Find luxury properties in Riyadh under SAR 2 million"
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) >= 1
    tool_name, args = plan[0]
    assert tool_name == "search_wasalt_properties"
    assert args.get("max_budget_sar") == 2000000.0
    assert args.get("city") == "Riyadh"

def test_plan_comparison_query(orchestrator):
    # Example 2: Compare DarGlobal projects in Dubai with properties in Riyadh on Wasalt
    query = "Compare DarGlobal projects in Dubai with properties in Riyadh on Wasalt"
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) == 2
    tools_selected = [p[0] for p in plan]
    assert "search_darglobal_projects" in tools_selected
    assert "search_wasalt_properties" in tools_selected

@pytest.mark.asyncio
async def test_agent_run_execution_trace_authenticity(orchestrator):
    # Execute query through agent
    req = ChatRequest(message="What luxury properties are available in Riyadh on Wasalt under SAR 5 million?")
    res = await orchestrator.run_agent(req)

    # 1. Answer is returned
    assert len(res.answer) > 50
    # 2. Execution trace is NOT empty and NEVER faked
    assert len(res.execution_trace) >= 1
    first_trace = res.execution_trace[0]
    assert first_trace.tool_name == "search_wasalt_properties"
    assert first_trace.status == "SUCCESS"
    assert first_trace.execution_time_ms > 0
    assert "output" in first_trace.model_dump()
    # 3. Citations are extracted and verified
    assert len(res.citations) >= 1
    assert any("wasalt.sa" in c.url for c in res.citations)

@pytest.mark.asyncio
async def test_agent_comparison_execution(orchestrator):
    req = ChatRequest(message="Compare Pagani DaVinci tower with Al Malqa villa in Riyadh")
    res = await orchestrator.run_agent(req)
    assert len(res.execution_trace) >= 1
    assert len(res.citations) >= 1

@pytest.mark.asyncio
async def test_agent_loop_prevention(orchestrator):
    # Artificially inject duplicate planned calls
    original_plan = orchestrator.plan_tools_from_query
    try:
        orchestrator.plan_tools_from_query = lambda q, sf=None, **kwargs: [
            ("search_darglobal_projects", {"query": "Pagani"}),
            ("search_darglobal_projects", {"query": "Pagani"}),  # duplicate call
            ("search_darglobal_projects", {"query": "Pagani"}),  # duplicate call
        ]
        req = ChatRequest(message="Pagani test loop")
        res = await orchestrator.run_agent(req)
        # Duplicate call should be skipped by loop prevention
        assert len(res.execution_trace) == 1
    finally:
        orchestrator.plan_tools_from_query = original_plan

@pytest.mark.asyncio
async def test_agent_tool_validation_error(orchestrator):
    # Call tool with invalid arguments
    trace = await orchestrator.execute_tool(
        step=1,
        tool_name="compare_properties",
        raw_arguments={"property_names_or_ids": ["only_one_item"]} # Fails min_length=2
    )
    assert trace.status == "ERROR"
    assert "validation failed" in trace.error.lower()

# --- Conversational Intent Detection & Agent Routing Tests ---

def test_greeting_hi(orchestrator):
    # 1. "Hi" -> No tools.
    query = "Hi"
    intent, _ = orchestrator.classify_intent(query)
    assert intent == IntentType.GREETING
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) == 0

def test_greeting_hello(orchestrator):
    # 2. "Hello" -> No tools.
    query = "Hello"
    intent, _ = orchestrator.classify_intent(query)
    assert intent == IntentType.GREETING
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) == 0

def test_general_thank_you(orchestrator):
    # 3. "Thank you" -> No tools.
    query = "Thank you"
    intent, _ = orchestrator.classify_intent(query)
    assert intent == IntentType.GENERAL_CONVERSATION
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) == 0

def test_general_what_can_you_do(orchestrator):
    # 4. "What can you do?" -> No tools.
    query = "What can you do?"
    intent, _ = orchestrator.classify_intent(query)
    assert intent == IntentType.GENERAL_CONVERSATION
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) == 0

def test_property_search_wasalt_riyadh(orchestrator):
    # 5. "Find properties in Riyadh" -> Wasalt search.
    query = "Find properties in Riyadh"
    intent, _ = orchestrator.classify_intent(query)
    assert intent == IntentType.PROPERTY_SEARCH
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) >= 1
    tool_names = [p[0] for p in plan]
    assert "search_wasalt_properties" in tool_names

def test_project_search_darglobal_dubai(orchestrator):
    # 6. "DarGlobal projects in Dubai" -> DarGlobal search.
    query = "DarGlobal projects in Dubai"
    intent, _ = orchestrator.classify_intent(query)
    assert intent == IntentType.PROJECT_SEARCH
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) >= 1
    tool_names = [p[0] for p in plan]
    assert "search_darglobal_projects" in tool_names

def test_property_comparison_intent(orchestrator):
    # 7. "Compare these properties" -> Comparison tool.
    query = "Compare these properties"
    intent, _ = orchestrator.classify_intent(query)
    assert intent == IntentType.PROPERTY_COMPARISON
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) >= 1
    tool_names = [p[0] for p in plan]
    assert any("compare" in t or "search" in t for t in tool_names)

def test_follow_up_amenities_resolution(orchestrator):
    # 8. "What are its amenities?" -> Follow-up resolution using history.
    history = [
        ChatMessage(role="user", content="Tell me about DaVinci Tower."),
        ChatMessage(role="assistant", content="DaVinci Tower by Pagani is a residential masterpiece located on the Dubai Canal.")
    ]
    query = "What are its amenities?"
    intent, params = orchestrator.classify_intent(query, history=history)
    assert intent in [IntentType.FOLLOW_UP, IntentType.PROJECT_DETAILS]
    plan = orchestrator.plan_tools_from_query(query, history=history)
    assert len(plan) == 1
    tool_name, args = plan[0]
    assert tool_name == "get_project_details"
    assert args.get("project_id") == "dg-pagani-geometria"

def test_compound_greeting_and_property_search(orchestrator):
    # 9. "Good morning, find villas in Riyadh" -> Property search, not greeting-only response.
    query = "Good morning, find villas in Riyadh"
    intent, params = orchestrator.classify_intent(query)
    assert intent == IntentType.PROPERTY_SEARCH
    plan = orchestrator.plan_tools_from_query(query)
    assert len(plan) >= 1
    tool_names = [p[0] for p in plan]
    assert "search_wasalt_properties" in tool_names
    assert plan[0][1].get("city") == "Riyadh"

@pytest.mark.asyncio
async def test_greeting_run_agent_no_tools(orchestrator):
    # Test that run_agent executes zero tools and outputs no execution trace for greetings
    req = ChatRequest(message="hi")
    res = await orchestrator.run_agent(req)
    assert len(res.execution_trace) == 0
    assert len(res.citations) == 0
    assert "Welcome to DarGlobal Intelligence" in res.answer
    assert res.intent == "GREETING"

