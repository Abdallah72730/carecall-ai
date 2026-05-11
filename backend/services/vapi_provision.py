"""Per-clinic Vapi assistant provisioning.

One assistant per clinic so each has its own phone number, transfer
destination, and (eventually) branded greeting. The shared `/vapi`
backend endpoint handles routing by reading the assistant id Vapi
attaches to each chat-completion request, so adding clinics is just:

    create_assistant_for_clinic("<uuid>")

Idempotent: returns the existing assistant id if the clinic already
has one.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from config import require
from db import supabase_admin

logger = logging.getLogger(__name__)

VAPI_API_BASE = "https://api.vapi.ai"
# Backend base for the custom-LLM proxy. Hardcoded here on purpose —
# this URL is what every assistant points at and it changes rarely.
BACKEND_BASE = "https://backend-production-d0cf2.up.railway.app"


def _base_payload(clinic_name: str) -> dict[str, Any]:
    return {
        "name": f"CareCall AI · {clinic_name}",
        "model": {
            "provider": "custom-llm",
            "url": f"{BACKEND_BASE}/vapi",
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.4,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are CareCall, the AI receptionist for "
                        f"{clinic_name}, a healthcare clinic in Alberta, "
                        "Canada. Disclose that you are an AI if asked. "
                        "Replies must be very short — usually one sentence "
                        "— and conversational. The system injects KB and "
                        "OPEN/CLOSED context every turn; treat those as "
                        "your only source of truth. Never give medical "
                        "advice. Never store health information such as "
                        "symptoms, diagnoses, or medications."
                    ),
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "save_message",
                        "description": (
                            "Save the after-hours message. Only call after "
                            "collecting caller_name AND caller_phone AND "
                            "message_reason, and after reading them back "
                            "for confirmation."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "caller_name": {"type": "string"},
                                "caller_phone": {"type": "string"},
                                "message_reason": {"type": "string"},
                            },
                            "required": [
                                "caller_name",
                                "caller_phone",
                                "message_reason",
                            ],
                        },
                    },
                    "server": {"url": f"{BACKEND_BASE}/vapi/save-message"},
                }
            ],
        },
        "voice": {
            "provider": "cartesia",
            "voiceId": "248be419-c632-4f23-adf1-5324ed7dbf1d",
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en",
            "endpointing": 500,
        },
        "firstMessage": (
            f"Hi, this is CareCall — {clinic_name}'s AI receptionist. "
            "I'm an AI, not a real person. How can I help you today?"
        ),
        "startSpeakingPlan": {"waitSeconds": 1.5, "smartEndpointingEnabled": True},
        "stopSpeakingPlan": {
            "numWords": 5,
            "voiceSeconds": 0.4,
            "backoffSeconds": 1.0,
        },
        "silenceTimeoutSeconds": 30,
    }


def _attach_transfer_tool(payload: dict[str, Any], transfer_number: str | None) -> None:
    """Add Vapi's built-in transferCall tool in blind mode.

    Blind transfer means the AI hangs up the moment the call is handed
    over, so Vapi stops billing the LLM session. The receptionist sees
    a normal inbound call on their forwarding line — no AI in the loop.
    """
    if not transfer_number:
        return
    payload["model"]["tools"].append(
        {
            "type": "transferCall",
            "destinations": [
                {
                    "type": "number",
                    "number": transfer_number,
                    "message": "Connecting you to the front desk now.",
                    "transferPlan": {"mode": "blind-transfer"},
                }
            ],
        }
    )


def create_assistant_for_clinic(clinic_id: str) -> str:
    """Provision a fresh Vapi assistant for a clinic, or return the
    existing assistant id if one is already linked.

    Side effect: writes `vapi_assistant_id` back to the clinic row on
    first create.
    """
    client = supabase_admin()
    res = (
        client.table("clinics")
        .select("id,name,vapi_assistant_id,transfer_number")
        .eq("id", clinic_id)
        .limit(1)
        .single()
        .execute()
    )
    clinic = res.data
    if not clinic:
        raise ValueError(f"Clinic {clinic_id} not found")

    existing = clinic.get("vapi_assistant_id")
    if existing:
        logger.info("clinic %s already has assistant %s", clinic_id, existing)
        return existing

    payload = _base_payload(clinic.get("name") or "the clinic")
    _attach_transfer_tool(payload, clinic.get("transfer_number"))

    headers = {
        "Authorization": f"Bearer {require('VAPI_API_KEY')}",
        "Content-Type": "application/json",
    }
    resp = httpx.post(
        f"{VAPI_API_BASE}/assistant",
        json=payload,
        headers=headers,
        timeout=30.0,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Vapi create-assistant failed: {resp.status_code} {resp.text}")
    assistant_id = resp.json()["id"]

    client.table("clinics").update({"vapi_assistant_id": assistant_id}).eq(
        "id", clinic_id
    ).execute()
    logger.info("provisioned Vapi assistant %s for clinic %s", assistant_id, clinic_id)
    return assistant_id


def update_assistant_transfer(clinic_id: str) -> bool:
    """Refresh the transferCall tool on an existing assistant after a
    clinic's transfer_number is changed in the dashboard. Returns True
    if a Vapi PATCH was sent.
    """
    client = supabase_admin()
    res = (
        client.table("clinics")
        .select("vapi_assistant_id,transfer_number,name")
        .eq("id", clinic_id)
        .limit(1)
        .single()
        .execute()
    )
    clinic = res.data
    if not clinic or not clinic.get("vapi_assistant_id"):
        return False

    payload: dict[str, Any] = {"model": {"tools": []}}
    # We re-send the save_message tool every time because Vapi PATCH
    # replaces the whole tools array.
    tools = [
        {
            "type": "function",
            "function": {
                "name": "save_message",
                "description": "Save the after-hours message.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "caller_name": {"type": "string"},
                        "caller_phone": {"type": "string"},
                        "message_reason": {"type": "string"},
                    },
                    "required": [
                        "caller_name",
                        "caller_phone",
                        "message_reason",
                    ],
                },
            },
            "server": {"url": f"{BACKEND_BASE}/vapi/save-message"},
        }
    ]
    if clinic.get("transfer_number"):
        tools.append(
            {
                "type": "transferCall",
                "destinations": [
                    {
                        "type": "number",
                        "number": clinic["transfer_number"],
                        "message": "Connecting you to the front desk now.",
                        "transferPlan": {"mode": "blind-transfer"},
                    }
                ],
            }
        )
    payload["model"]["tools"] = tools

    headers = {
        "Authorization": f"Bearer {require('VAPI_API_KEY')}",
        "Content-Type": "application/json",
    }
    resp = httpx.patch(
        f"{VAPI_API_BASE}/assistant/{clinic['vapi_assistant_id']}",
        json=payload,
        headers=headers,
        timeout=30.0,
    )
    if resp.status_code >= 400:
        logger.warning(
            "Vapi PATCH for assistant %s failed: %s %s",
            clinic["vapi_assistant_id"],
            resp.status_code,
            resp.text[:300],
        )
        return False
    return True
