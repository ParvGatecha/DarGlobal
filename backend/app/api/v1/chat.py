import json
from typing import Optional
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.llm.rag_engine import RAGEngine
from backend.app.agent.orchestrator import AgentOrchestrator

router = APIRouter()

def get_rag_engine(request: Request) -> RAGEngine:
    return request.app.state.rag_engine

def get_agent_orchestrator(request: Request) -> Optional[AgentOrchestrator]:
    return getattr(request.app.state, "agent_orchestrator", None)

@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    chat_req: ChatRequest,
    agent_orchestrator: Optional[AgentOrchestrator] = Depends(get_agent_orchestrator),
    rag_engine: RAGEngine = Depends(get_rag_engine)
) -> ChatResponse:
    """
    Conversational Agent endpoint with genuine tool orchestration,
    Pydantic argument validation, execution timeouts, loop prevention,
    and verified source citations.
    """
    if agent_orchestrator:
        return await agent_orchestrator.run_agent(chat_req)
    return await rag_engine.answer_query(chat_req)

@router.post("/stream")
async def chat_stream_endpoint(
    chat_req: ChatRequest,
    agent_orchestrator: Optional[AgentOrchestrator] = Depends(get_agent_orchestrator),
    rag_engine: RAGEngine = Depends(get_rag_engine)
):
    """
    Server-Sent Events (SSE) streaming conversational agent endpoint.
    Streams tool execution traces, citations metadata, and token deltas in real time.
    """
    async def event_generator():
        if agent_orchestrator:
            async for event in agent_orchestrator.stream_agent(chat_req):
                yield {
                    "event": "message",
                    "data": json.dumps(event)
                }
        else:
            async for event in rag_engine.stream_query(chat_req):
                yield {
                    "event": "message",
                    "data": json.dumps(event)
                }

    return EventSourceResponse(event_generator())
