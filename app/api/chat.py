"""Streaming chat endpoint for chart Q&A using Haiku via SSE."""
import json
from typing import AsyncGenerator

import anthropic
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supabase import Client

from app.api.deps import get_chart_or_404, get_db
from app.core.config import settings
from app.db import queries
from app.services.harness.context_builder import build_chat_context
from app.agents.prompts.chat import SYSTEM_PROMPT

CHAT_MODEL = "claude-haiku-4-5"

router = APIRouter(prefix="/api/charts", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


async def _stream_chat(
    user_message: str,
    chart_context: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Build message history for the API call
    messages: list[dict] = [{"role": "user", "content": chart_context}]
    # Insert a brief assistant acknowledgement to establish context
    messages.append({"role": "assistant", "content": "I have your chart data. What would you like to know?"})

    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    async with client.messages.stream(
        model=CHAT_MODEL,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/{chart_id}/chat")
async def chat(
    request: ChatRequest,
    chart: dict = Depends(get_chart_or_404),
    db: Client = Depends(get_db),
):
    """Stream a chat response about the chart. Returns SSE."""
    history = queries.get_chat_history(db, chart["id"], limit=20)
    chart_context = build_chat_context(chart)

    # Save user message before streaming (so it persists even if client disconnects)
    queries.insert_chat_message(db, chart["id"], "user", request.message)

    # Collect full response to persist — we buffer while streaming
    collected: list[str] = []

    async def event_stream() -> AsyncGenerator[str, None]:
        async for chunk in _stream_chat(request.message, chart_context, history):
            if chunk != "data: [DONE]\n\n":
                try:
                    payload = json.loads(chunk[6:])
                    collected.append(payload.get("text", ""))
                except Exception:
                    pass
            yield chunk
        # Persist assistant response after stream completes
        full_response = "".join(collected)
        if full_response:
            queries.insert_chat_message(db, chart["id"], "assistant", full_response)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{chart_id}/chat/history")
async def get_chat_history(
    chart: dict = Depends(get_chart_or_404),
    db: Client = Depends(get_db),
):
    """Return the last 50 messages for a chart."""
    return queries.get_chat_history(db, chart["id"], limit=50)
