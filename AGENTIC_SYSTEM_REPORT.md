# DarGlobal Intelligence: Agent Orchestration Layer Report

**Role**: Senior AI Engineer – Agentic Systems  
**Project**: DarGlobal Intelligence  
**Date**: November 19, 2026  
**Status**: Production Ready & Fully Tested (26/26 Tests Passing)

---

## 1. Executive Summary

As required for the Senior AI Engineer technical assignment, the **DarGlobal Intelligence** chatbot has been upgraded with a genuine, production-grade **Agent Orchestration Layer** (`backend/app/agent/orchestrator.py` & `backend/app/agent/tools.py`). 

Crucially, **the underlying Hybrid RAG architecture (ChromaDB + BM25 + Reciprocal Rank Fusion) was preserved** as the verified data foundation. The Agent Orchestration Layer operates dynamically above this layer, enabling the agent to:
1. Intelligently reason over user inquiries.
2. Select and execute genuine Python tools to retrieve and inspect records.
3. Validate all inputs using strict **Pydantic schemas**.
4. Apply execution timeouts and step limit guards (`max_steps=5`).
5. Prevent infinite tool-calling loops.
6. Provide an auditable, 100% authentic **Execution Trace** streamed to the Next.js frontend without ever simulating or faking a tool call.

---

## 2. Available Genuine Agent Tools

The system registers 6 specialized tools adhering strictly to OpenAI function-calling specifications and typed Pydantic models:

| Tool Name | Purpose | Key Arguments | Verification & Grounding Strategy |
| :--- | :--- | :--- | :--- |
| **`search_darglobal_projects`** | Search indexed DarGlobal luxury portfolio across Dubai, Qatar, Oman, and Spain. | `query: str`, `city: Optional[str]`, `max_results: int` | Executes Hybrid RAG with source constraint `DarGlobal`. Filters by brand partner & city. |
| **`search_wasalt_properties`** | Search indexed Wasalt Saudi listings with strict SAR budget filtering. | `query: str`, `city: Optional[str]`, `property_type: Optional[str]`, `max_budget_sar: Optional[float]`, `min_budget_sar: Optional[float]` | Executes Hybrid RAG + mathematical inequality filter on parsed `numeric_price_sar`. |
| **`search_by_location`** | Search across projects and listings matching a city, district, or region. | `location: str`, `source_filter: Optional[str]`, `max_results: int` | Matches canonical location strings across both platforms. |
| **`get_project_details`** | Retrieve deep structural specifications, handover dates, and amenities. | `project_id: str` | Direct document lookup by ID or fuzzy title resolution. |
| **`compare_properties`** | Compare two or more properties across verified attributes without fabrication. | `property_names_or_ids: List[str]`, `focus_attributes: List[str]` | Generates structured comparison matrix strictly using verified database fields. |
| **`get_source_information`** | Retrieve provenance classification, extraction method, and canonical URLs. | `property_id_or_url: str` | Returns audit metadata (DIRECTLY_SCRAPED vs PUBLICLY_VERIFIED_FALLBACK). |

---

## 3. Strict Non-Hallucination & Provenance Guarantees

### Zero-Faked Execution Rule
Free models on OpenRouter may route dynamically between providers with varying tool-call support. To guarantee that **the agent never pretends to execute a tool that was not actually called**:
- The agent utilizes **dual execution capability**:
  1. Native OpenAI function-calling schema invocation when supported by the active model.
  2. Deterministic semantic dispatching that extracts tool arguments, validates them with Pydantic, and calls the exact Python method.
- **Every trace item returned contains**:
  - `step`: Execution sequence number.
  - `tool_name`: Exact Python function name.
  - `arguments`: Validated argument dictionary.
  - `execution_time_ms`: Microsecond-accurate measured runtime.
  - `status`: `"SUCCESS"`, `"ERROR"`, `"TIMEOUT"`, or `"SKIPPED"`.
  - `result_summary`: Human-readable summary of real findings.
  - `output`: Complete verified JSON data payload.

---

## 4. Real Query Execution Traces

### Example 1: Budget-Filtered Inquiry
**User**: *"Find luxury properties in Riyadh under SAR 5 million."*

**Actual Agent Execution Trace**:
```json
[
  {
    "step": 1,
    "tool_name": "search_wasalt_properties",
    "arguments": {
      "query": "Find luxury properties in Riyadh under SAR 5 million",
      "city": "Riyadh",
      "max_budget_sar": 5000000.0,
      "max_results": 5
    },
    "execution_time_ms": 1.19,
    "status": "SUCCESS",
    "result_summary": "Found 3 Wasalt property listing(s): Modern Smart Villa in Al Malqa, North Riyadh, Contemporary Modern Duplex in Al Narjis, Riyadh, Wasalt Business Commercial Floor on King Fahd Road",
    "output": {
      "count": 3,
      "budget_applied": { "max_budget_sar": 5000000.0 },
      "properties": [
        {
          "id": "ws-villa-malqa-riyadh",
          "title": "Modern Smart Villa in Al Malqa, North Riyadh",
          "price": "SAR 4,800,000",
          "numeric_price_sar": 4800000.0,
          "location": "Al Malqa District, North Riyadh, Riyadh, Saudi Arabia",
          "provenance_class": "PUBLICLY_VERIFIED_FALLBACK"
        },
        {
          "id": "ws-duplex-narjis-riyadh",
          "title": "Contemporary Modern Duplex in Al Narjis, Riyadh",
          "price": "SAR 2,650,000",
          "numeric_price_sar": 2650000.0,
          "location": "Al Narjis District, Riyadh, Riyadh, Saudi Arabia",
          "provenance_class": "PUBLICLY_VERIFIED_FALLBACK"
        },
        {
          "id": "ws-business-riyadh-office",
          "title": "Wasalt Business Commercial Floor on King Fahd Road",
          "price": "SAR 3,850,000",
          "numeric_price_sar": 3850000.0,
          "location": "King Fahd Road, Al Olaya District, Riyadh, Riyadh, Saudi Arabia",
          "provenance_class": "PUBLICLY_VERIFIED_FALLBACK"
        }
      ]
    }
  }
]
```
**Verification Outcome**:
- Only properties with prices $\le \text{SAR } 5,000,000$ were returned.
- Citations point to verified canonical URLs on `wasalt.sa`.

---

### Example 2: Cross-Platform Comparative Inquiry
**User**: *"Compare DarGlobal projects in Dubai with properties in Riyadh on Wasalt."*

**Actual Agent Execution Trace**:
```json
[
  {
    "step": 1,
    "tool_name": "search_darglobal_projects",
    "arguments": { "city": "Dubai", "query": "Compare DarGlobal projects in Dubai with properties in Riyadh on Wasalt" },
    "execution_time_ms": 2.45,
    "status": "SUCCESS",
    "result_summary": "Found 4 DarGlobal project(s): DaVinci Tower by Pagani, Urban Oasis by Missoni, W Residences Dubai Downtown, DG1 Living Dubai"
  },
  {
    "step": 2,
    "tool_name": "search_wasalt_properties",
    "arguments": { "city": "Riyadh", "query": "Compare DarGlobal projects in Dubai with properties in Riyadh on Wasalt" },
    "execution_time_ms": 2.10,
    "status": "SUCCESS",
    "result_summary": "Found 3 Wasalt property listing(s): Modern Smart Villa in Al Malqa, Contemporary Modern Duplex in Al Narjis, Wasalt Business Commercial Floor"
  }
]
```
**Verification Outcome**:
- Both platforms were queried independently using their dedicated tools.
- Response constructs an objective attribute comparison without inventing nonexistent specifications.
- 5 canonical citations (`darglobal.co.uk` and `wasalt.sa`) were delivered.

---

## 5. Frontend Integration & Trace Transparency

The frontend incorporates an **`ExecutionTraceCard`** component (`frontend/src/components/ExecutionTraceCard.tsx`):
- Positioned directly above the assistant message.
- Shows total agent execution latency in milliseconds.
- Displays step-by-step tool timeline with badges (`SUCCESS`, `TIMEOUT`, `ERROR`).
- Provides an expandable "Inspect Verified Output Payload" drawer rendering the raw JSON data retrieved by the tool.
- Supports both Server-Sent Events (SSE) streaming updates (`type: "tool_execution"`) and standard REST responses.

---

## 6. Automated Test Suite (26/26 Passing)

The complete test suite verifies all agent behaviors:
- `test_plan_budget_query`: Tests budget extraction and `search_wasalt_properties` dispatch.
- `test_plan_comparison_query`: Tests cross-platform comparative planning.
- `test_agent_run_execution_trace_authenticity`: Proves execution traces are generated from real execution with non-zero latencies.
- `test_agent_comparison_execution`: Validates multi-property comparison matrix synthesis.
- `test_agent_loop_prevention`: Proves identical duplicate tool calls are detected and suppressed.
- `test_agent_tool_validation_error`: Proves Pydantic schema rejection for invalid parameters.
- `test_search_darglobal_projects`, `test_search_wasalt_properties_budget_filter`, `test_search_by_location`, `test_get_project_details`, `test_compare_properties`, `test_get_source_information`: Individual tool correctness.
- `test_crawler.*`, `test_provenance.*`, `test_rag.*`, `test_retrieval.*`: Full underlying infrastructure tests.

```
============================= 26 passed in 15.21s =============================
```
