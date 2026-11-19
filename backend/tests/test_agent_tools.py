import pytest
from backend.app.retrieval.vector_store import VectorStore
from backend.app.retrieval.bm25_store import BM25Store
from backend.app.retrieval.hybrid_search import HybridSearchEngine
from backend.app.ingestion.seed_data import get_all_indexed_items
from backend.app.ingestion.chunker import SemanticChunker
from backend.app.agent.tools import (
    AgentToolRegistry,
    SearchDarGlobalInput,
    SearchWasaltInput,
    SearchByLocationInput,
    GetProjectDetailsInput,
    ComparePropertiesInput,
    GetSourceInformationInput,
)

@pytest.fixture(scope="module")
def agent_tools():
    v_store = VectorStore(persist_directory="./data/test_agent_chroma")
    b_store = BM25Store(index_path="./data/test_agent_bm25.pkl")
    chunker = SemanticChunker()

    all_chunks = []
    for item in get_all_indexed_items():
        all_chunks.extend(chunker.chunk_property(item))

    v_store.add_chunks(all_chunks)
    b_store.index_chunks(all_chunks)
    retriever = HybridSearchEngine(vector_store=v_store, bm25_store=b_store)
    return AgentToolRegistry(retriever=retriever)

def test_search_darglobal_projects(agent_tools):
    # 1. Search for Pagani
    res = agent_tools.search_darglobal_projects(SearchDarGlobalInput(query="Pagani DaVinci", max_results=3))
    assert res["count"] >= 1
    p = res["projects"][0]
    assert "pagani" in p["title"].lower() or "davinci" in p["title"].lower()
    assert p["source"] == "DarGlobal"
    assert "https://www.darglobal.co.uk" in p["url"]

    # 2. Search with city filter
    res_spain = agent_tools.search_darglobal_projects(SearchDarGlobalInput(query="villas", city="Marbella"))
    assert res_spain["count"] >= 1
    assert any("tierra viva" in x["title"].lower() for x in res_spain["projects"])

def test_search_wasalt_properties_budget_filter(agent_tools):
    # Budget filter under SAR 2,000,000
    res = agent_tools.search_wasalt_properties(SearchWasaltInput(
        query="apartment",
        max_budget_sar=2000000.0,
        max_results=5
    ))
    assert res["count"] >= 1
    for prop in res["properties"]:
        num_price = prop.get("numeric_price_sar")
        if num_price is not None:
            assert num_price <= 2000000.0

    # Ensure higher priced mansion (SAR 8.2M) is excluded under SAR 3M budget
    res_filtered = agent_tools.search_wasalt_properties(SearchWasaltInput(
        query="luxury",
        max_budget_sar=3000000.0
    ))
    for prop in res_filtered["properties"]:
        assert prop["id"] != "ws-mansion-hada-riyadh"

def test_search_by_location(agent_tools):
    # Location Riyadh
    res = agent_tools.search_by_location(SearchByLocationInput(location="Riyadh"))
    assert res["count"] >= 1
    assert any("riyadh" in m["location"].lower() or "riyadh" in m["city"].lower() for m in res["matches"])

    # Location Marbella
    res_marbella = agent_tools.search_by_location(SearchByLocationInput(location="Marbella"))
    assert res_marbella["count"] >= 1
    assert any("spain" in m["country"].lower() or "marbella" in m["city"].lower() for m in res_marbella["matches"])

def test_get_project_details(agent_tools):
    # By ID
    res = agent_tools.get_project_details(GetProjectDetailsInput(project_id="dg-pagani-geometria"))
    assert res["found"] is True
    assert "Pagani" in res["title"]
    assert len(res["amenities"]) >= 4
    assert res["provenance_class"] == "PUBLICLY_VERIFIED_FALLBACK"

    # By Name
    res_name = agent_tools.get_project_details(GetProjectDetailsInput(project_name="Urban Oasis"))
    assert res_name["found"] is True
    assert "Missoni" in res_name["brand_partner"]

    # Non-existent project
    res_missing = agent_tools.get_project_details(GetProjectDetailsInput(project_name="Atlantis Tower Underwater"))
    assert "error" in res_missing
    assert len(res_missing["available_projects_suggestion"]) > 0

def test_compare_properties(agent_tools):
    # Valid comparison
    res = agent_tools.compare_properties(ComparePropertiesInput(
        property_names_or_ids=["dg-pagani-geometria", "ws-villa-malqa-riyadh"],
        focus_attributes=["price", "location", "property_type"]
    ))
    assert res["comparison_count"] == 2
    props = res["compared_properties"]
    assert props[0]["source"] != props[1]["source"] # One DarGlobal, one Wasalt
    assert "verification_note" in res

    # Invalid comparison (single property)
    res_invalid = agent_tools.compare_properties(ComparePropertiesInput(
        property_names_or_ids=["dg-pagani-geometria", "unknown-fantasy-castle"]
    ))
    assert "error" in res_invalid

def test_get_source_information(agent_tools):
    # Query for DarGlobal project
    res = agent_tools.get_source_information(GetSourceInformationInput(query_or_url="dg-pagani-geometria"))
    assert res["found"] is True
    assert res["provenance_class"] == "PUBLICLY_VERIFIED_FALLBACK"
    assert "Imperva" in res["origin_notes"]

    # Query for directly scraped sitemap
    res_sitemap = agent_tools.get_source_information(GetSourceInformationInput(query_or_url="sitemap.xml"))
    assert res_sitemap["found"] is True
    assert res_sitemap["provenance_class"] == "DIRECTLY_SCRAPED"
    assert res_sitemap["is_directly_scraped"] is True
