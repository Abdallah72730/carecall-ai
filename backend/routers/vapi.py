"""Vapi-facing endpoints: custom LLM proxy, webhook, end-of-call hook."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from config import require
from db import supabase_admin
from services.clinics import clinic_id_for_assistant
from services.knowledge import format_context, search_faqs

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

KB_INSTRUCTION = (
    "Use the following knowledge base to answer the caller's question. "
    "If the answer is not in the knowledge base, say you'll take a "
    "message and have someone from the clinic call them back. Never "
    "invent details about the clinic.\n\n"
)


def _last_user_text(messages: list[dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return " ".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
    return ""


def _inject_kb_context(messages: list[dict[str, Any]], context: str) -> list[dict[str, Any]]:
    """Insert a system message with KB context just before the latest user turn."""
    insert_at = len(messages)
    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx].get("role") == "user":
            insert_at = idx
            break
    new_messages = list(messages)
    new_messages.insert(insert_at, {"role": "system", "content": KB_INSTRUCTION + context})
    return new_messages


@router.post("/chat/completions")
async def llm_proxy(request: Request) -> StreamingResponse:
    """OpenAI-compatible chat completions, proxied to Groq.

    Before forwarding, look up the clinic via the Vapi assistant id
    and inject any relevant FAQs as a system message so the model can
    answer from the knowledge base.
    """
    raw: dict[str, Any] = await request.json()
    body = {k: v for k, v in raw.items() if k in OPENAI_ALLOWED_FIELDS}
    body["model"] = GROQ_MODEL

    assistant_id = (raw.get("assistant") or {}).get("id")
    clinic_id = clinic_id_for_assistant(assistant_id)
    if clinic_id and isinstance(body.get("messages"), list) and body["messages"]:
        user_text = _last_user_text(body["messages"])
        if user_text:
            faqs = search_faqs(clinic_id, user_text)
            if faqs:
                body["messages"] = _inject_kb_context(body["messages"], format_context(faqs))
                logger.info("Injected %d FAQ(s) for clinic=%s", len(faqs), clinic_id)

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


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.post("/webhook")
async def webhook(request: Request) -> dict:
    """Generic Vapi webhook. Handles end-of-call reports and tool calls.

    For tool calls, Vapi expects {"results": [{toolCallId, result}]}.
    For other events, just acknowledge — never raise.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"received": True}
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    msg_type = message.get("type")

    if msg_type in {"tool-calls", "function-call"}:
        return _handle_tool_calls(message)
    if msg_type == "end-of-call-report":
        _persist_call_log(message)
    return {"received": True}


@router.post("/end-of-call")
async def end_of_call(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception:
        return {"received": True}
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    _persist_call_log(message)
    return {"received": True}


def _handle_tool_calls(message: dict[str, Any]) -> dict:
    """Resolve get_clinic_info / save_message tool calls. Always return results."""
    assistant_id = (message.get("call") or {}).get("assistantId") or (
        message.get("assistant") or {}
    ).get("id")
    clinic_id = clinic_id_for_assistant(assistant_id)

    results: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = (
        message.get("toolCalls")
        or message.get("toolCallList")
        or ([message["functionCall"]] if message.get("functionCall") else [])
    )
    for call in tool_calls:
        tc_id = call.get("id") or call.get("toolCallId")
        fn = call.get("function") or call
        name = fn.get("name")
        args = fn.get("arguments") or fn.get("parameters") or {}
        if isinstance(args, str):
            try:
                import json as _json

                args = _json.loads(args)
            except Exception:
                args = {}

        if name == "get_clinic_info" and clinic_id:
            query = (args or {}).get("query", "")
            faqs = search_faqs(clinic_id, query)
            text = format_context(faqs) or "No matching information in the knowledge base."
            results.append({"toolCallId": tc_id, "result": text})
        else:
            results.append({"toolCallId": tc_id, "result": ""})
    return {"results": results}


def _persist_call_log(message: dict[str, Any]) -> None:
    call = message.get("call") or {}
    vapi_call_id = call.get("id")
    if not vapi_call_id:
        return
    assistant_id = call.get("assistantId") or (message.get("assistant") or {}).get("id")
    clinic_id = clinic_id_for_assistant(assistant_id)
    if not clinic_id:
        logger.info("end-of-call: no clinic for assistant=%s, skipping", assistant_id)
        return

    started_at = _parse_iso(message.get("startedAt") or call.get("createdAt"))
    ended_at = _parse_iso(message.get("endedAt") or message.get("timestamp"))
    duration = None
    if started_at and ended_at:
        duration = max(int((ended_at - started_at).total_seconds()), 0)

    row = {
        "clinic_id": clinic_id,
        "vapi_call_id": vapi_call_id,
        "started_at": (started_at or datetime.now(timezone.utc)).isoformat(),
        "ended_at": ended_at.isoformat() if ended_at else None,
        "duration_seconds": duration,
        "call_summary": message.get("summary") or message.get("analysis", {}).get("summary"),
        "caller_number": (message.get("customer") or {}).get("number"),
    }
    try:
        supabase_admin().table("call_logs").upsert(row, on_conflict="vapi_call_id").execute()
    except Exception as exc:
        logger.warning("call_log upsert failed: %s", exc)
