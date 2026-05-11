"""Vapi-facing endpoints: custom LLM proxy, webhook, end-of-call hook."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from config import require, settings
from db import supabase_admin
from services.clinics import clinic_id_for_assistant, is_clinic_live
from services.email import send_message_alert
from services.hours import get_clinic_for_email, is_clinic_open
from services.knowledge import format_context, search_faqs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vapi", tags=["vapi"])

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Cerebras Inference (US-based) is the fallback when Groq rate-limits or
# errors. Same Llama 3.3 70B family, OpenAI-compatible API.
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
CEREBRAS_MODEL = "llama-3.3-70b"

# Status codes that mean "Groq said no, try someone else." 429 is rate
# limit; 5xx is upstream failure. Anything else (e.g. 400 on a bad prompt)
# we let surface — retrying won't help and would mask a real bug.
RETRY_STATUSES = {429, 500, 502, 503, 504}

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

    # Subscription gate: refuse politely if clinic is canceled/disabled.
    if clinic_id and not is_clinic_live(clinic_id):
        body["messages"] = list(body.get("messages") or []) + [
            {
                "role": "system",
                "content": (
                    "This clinic's CareCall AI subscription is not active. "
                    "Apologize briefly to the caller, tell them the clinic's "
                    "automated assistant is currently unavailable, and ask "
                    "them to call again later. Do not collect any messages "
                    "or use any tools. Keep the reply to one sentence."
                ),
            }
        ]
        # Skip FAQ / hours injection — go straight to LLM.
        clinic_id = None

    if clinic_id and isinstance(body.get("messages"), list) and body["messages"]:
        user_text = _last_user_text(body["messages"])
        # Inject FAQ context for the user's most recent question
        if user_text:
            faqs = search_faqs(clinic_id, user_text)
            if faqs:
                body["messages"] = _inject_kb_context(body["messages"], format_context(faqs))
                logger.info("Injected %d FAQ(s) for clinic=%s", len(faqs), clinic_id)
        # Inject open/closed status so the assistant knows when to take a message
        try:
            open_now = is_clinic_open(clinic_id)
        except Exception as exc:
            logger.warning("hours check failed for clinic=%s: %s", clinic_id, exc)
            open_now = True
        status_msg = (
            "The clinic is currently OPEN. Answer questions normally."
            if open_now
            else "The clinic is currently CLOSED. After answering any quick "
            "knowledge-base questions, gently offer to take a message: ask "
            "for the caller's name, phone number, and reason for calling, "
            "then call the save_message tool with those values."
        )
        body["messages"].insert(0, {"role": "system", "content": status_msg})

    media_type = "text/event-stream" if body.get("stream") else "application/json"

    async def upstream():
        # Try Groq first, then Cerebras on rate-limit or upstream failure.
        # Both speak OpenAI chat-completions; only the model name differs.
        providers = [
            ("groq", GROQ_BASE_URL, GROQ_MODEL, require("GROQ_API_KEY")),
        ]
        if settings.CEREBRAS_API_KEY:
            providers.append(
                ("cerebras", CEREBRAS_BASE_URL, CEREBRAS_MODEL, settings.CEREBRAS_API_KEY)
            )

        for idx, (name, base, model, key) in enumerate(providers):
            attempt = dict(body)
            attempt["model"] = model
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        f"{base}/chat/completions",
                        json=attempt,
                        headers=headers,
                    ) as resp:
                        if resp.status_code in RETRY_STATUSES and idx < len(providers) - 1:
                            err = (await resp.aread()).decode("utf-8", errors="replace")
                            logger.warning(
                                "%s %s — falling back: %s",
                                name, resp.status_code, err[:200],
                            )
                            continue
                        if resp.status_code >= 400:
                            err = (await resp.aread()).decode("utf-8", errors="replace")
                            logger.warning("%s %s: %s", name, resp.status_code, err[:500])
                            yield err.encode("utf-8")
                            return
                        async for chunk in resp.aiter_bytes():
                            yield chunk
                        return
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
                if idx < len(providers) - 1:
                    logger.warning("%s transport error — falling back: %s", name, exc)
                    continue
                logger.error("%s transport error, no fallback: %s", name, exc)
                yield f'{{"error":{{"message":"{name} unavailable"}}}}'.encode()
                return

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


@router.post("/save-message")
async def save_message_route(request: Request) -> dict:
    """Direct endpoint Vapi can hit as the save_message tool's server URL."""
    try:
        payload = await request.json()
    except Exception:
        return {"results": []}
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    return _handle_tool_calls(message)


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
        elif name == "save_message" and clinic_id:
            results.append(
                {"toolCallId": tc_id, "result": _save_after_hours_message(clinic_id, args, message)}
            )
        else:
            results.append({"toolCallId": tc_id, "result": ""})
    return {"results": results}


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _save_after_hours_message(
    clinic_id: str,
    args: dict[str, Any],
    message: dict[str, Any],
) -> str:
    caller_name = _clean((args or {}).get("caller_name") or (args or {}).get("name"))
    caller_phone = _clean((args or {}).get("caller_phone") or (args or {}).get("phone"))
    if not caller_phone:
        caller_phone = _clean((message.get("customer") or {}).get("number"))
    reason = _clean((args or {}).get("message_reason") or (args or {}).get("reason"))

    # Hard requirement: name + phone. Reason is also required by the prompt
    # but we accept a short fallback rather than hard-fail there.
    if not caller_name or not caller_phone:
        missing = []
        if not caller_name:
            missing.append("the caller's name")
        if not caller_phone:
            missing.append("a phone number")
        return (
            "I cannot save the message yet — I still need "
            + " and ".join(missing)
            + ". Please ask the caller for the missing detail and try again."
        )
    if not reason:
        reason = "(no reason given)"

    vapi_call_id = (message.get("call") or {}).get("id")

    # One message per call: if we already saved one for this call, don't duplicate.
    if vapi_call_id:
        try:
            already = (
                supabase_admin()
                .table("after_hours_messages")
                .select("id, call_logs!inner(vapi_call_id)")
                .eq("clinic_id", clinic_id)
                .eq("call_logs.vapi_call_id", vapi_call_id)
                .limit(1)
                .execute()
            ).data
        except Exception:
            already = None
        if already:
            return (
                "A message has already been saved for this call. Only take "
                "another if the caller explicitly asks to leave a second one."
            )

    call_log_id = None
    if vapi_call_id:
        try:
            existing = (
                supabase_admin()
                .table("call_logs")
                .select("id")
                .eq("vapi_call_id", vapi_call_id)
                .limit(1)
                .execute()
            ).data
            if existing:
                call_log_id = existing[0]["id"]
        except Exception:
            call_log_id = None

    row = {
        "clinic_id": clinic_id,
        "call_log_id": call_log_id,
        "caller_name": caller_name,
        "caller_phone": caller_phone,
        "message_reason": reason,
    }
    try:
        inserted = supabase_admin().table("after_hours_messages").insert(row).execute()
        message_id = inserted.data[0]["id"] if inserted.data else None
    except Exception as exc:
        logger.warning("after_hours_messages insert failed: %s", exc)
        return "Sorry, I had trouble saving that message. Please try again later."

    clinic = get_clinic_for_email(clinic_id)
    if clinic and clinic.get("email"):
        sent = send_message_alert(
            clinic_email=clinic["email"],
            clinic_name=clinic.get("name") or "the clinic",
            caller_name=caller_name,
            caller_phone=caller_phone,
            message_reason=reason,
        )
        if sent and message_id:
            try:
                supabase_admin().table("after_hours_messages").update(
                    {"email_sent": True}
                ).eq("id", message_id).execute()
            except Exception as exc:
                logger.warning("email_sent flag update failed: %s", exc)

    return (
        f"Message saved for {caller_name} at {caller_phone}. "
        "Someone from the clinic will call back during business hours. "
        "Do not take another message unless the caller asks for one."
    )


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
