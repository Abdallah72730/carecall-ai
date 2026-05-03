"""Vapi-facing endpoints: custom LLM proxy and call lifecycle hooks."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from config import require

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vapi", tags=["vapi"])

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Whitelist of OpenAI chat-completions fields. Vapi attaches its own
# context (assistant, call, customer, etc.) that Groq rejects with 400.
OPENAI_ALLOWED_FIELDS = {
    "model", "messages", "temperature", "top_p", "n", "stream", "stop",
    "max_tokens", "max_completion_tokens", "presence_penalty",
    "frequency_penalty", "logit_bias", "user", "tools", "tool_choice",
    "response_format", "seed", "logprobs", "top_logprobs",
    "stream_options", "parallel_tool_calls",
}


@router.post("/chat/completions")
async def llm_proxy(request: Request) -> StreamingResponse:
    """OpenAI-compatible chat completions, proxied to Groq.

    Vapi posts the live conversation here. The Vapi custom-LLM provider
    appends `/chat/completions` to the configured base URL, so this route
    lives at `/vapi/chat/completions` and the assistant's url is `/vapi`.
    We force the model to Groq's free-tier Llama 3.3 70B and stream the
    SSE response back unchanged.
    """
    raw: dict[str, Any] = await request.json()
    body = {k: v for k, v in raw.items() if k in OPENAI_ALLOWED_FIELDS}
    body["model"] = GROQ_MODEL

    headers = {
        "Authorization": f"Bearer {require('GROQ_API_KEY')}",
        "Content-Type": "application/json",
    }
    media_type = "text/event-stream" if body.get("stream") else "application/json"

    async def upstream():
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{GROQ_BASE_URL}/chat/completions",
                json=body,
                headers=headers,
            ) as resp:
                if resp.status_code >= 400:
                    err = (await resp.aread()).decode("utf-8", errors="replace")
                    logger.warning("Groq %s: %s", resp.status_code, err[:500])
                    yield err.encode("utf-8")
                    return
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(upstream(), media_type=media_type)


@router.post("/end-of-call")
async def end_of_call(request: Request) -> dict:
    """Vapi end-of-call report. Logged only at M2; persisted in M4."""
    try:
        payload = await request.json()
    except Exception:
        payload = None
    call = (payload or {}).get("message", {}).get("call") or {}
    logger.info(
        "end-of-call: id=%s assistant=%s",
        call.get("id"),
        call.get("assistantId"),
    )
    return {"received": True}
