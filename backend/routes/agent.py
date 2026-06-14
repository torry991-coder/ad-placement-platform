"""Agent REST API — LLM chat + SSE streaming agent pipeline."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import (
    AgentChatRequest,
    AgentChatResponse,
)
from backend.agents.pipeline import run_pipeline, run_pipeline_stream

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    body: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the LLM advertising agent and get a response.

    The agent can analyze campaigns, suggest optimizations, and recommend actions.
    Optionally provide campaign_id for context-aware responses.
    """
    try:
        result = await run_pipeline(
            message=body.message,
            campaign_id=body.campaign_id,
            context=body.context,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Agent chat failed: {exc}",
        )

    return AgentChatResponse(
        reply=result.get("reply", ""),
        actions=result.get("actions", []),
        suggestions=result.get("suggestions", []),
        model_used=result.get("model_used", "unknown"),
    )


@router.get("/stream")
async def agent_stream(
    request: Request,
    message: str = __import__("fastapi").Query(..., min_length=1),
    campaign_id: int | None = __import__("fastapi").Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Stream the agent's response via Server-Sent Events (SSE).

    Returns a stream of `data:` events containing response tokens,
    `event: suggestions` with follow-up suggestions, and `event: done`
    when the stream is complete.
    """
    async def event_generator():
        try:
            async for chunk in run_pipeline_stream(
                message=message,
                campaign_id=campaign_id,
            ):
                # If the client disconnects, stop streaming
                if await request.is_disconnected():
                    break
                yield chunk
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
