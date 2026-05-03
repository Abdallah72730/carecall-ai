"""Clinic admin endpoints. Every route requires a valid Supabase JWT."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from db import supabase_admin
from services.embedding import get_embedding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


async def get_clinic_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Verify the bearer JWT, resolve to clinic_id."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    client = supabase_admin()
    try:
        user_resp = client.auth.get_user(token)
        user_id = user_resp.user.id
    except Exception as exc:
        logger.info("Auth rejected: %s", exc)
        raise HTTPException(401, "Invalid token") from exc
    res = client.table("clinics").select("id").eq("user_id", user_id).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "No clinic linked to this user")
    return res.data[0]["id"]


ClinicId = Annotated[str, Depends(get_clinic_id)]


class FAQCreate(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    category: str | None = None


class FAQUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None


def _embed(question: str, answer: str) -> list[float]:
    return get_embedding(f"{question}\n{answer}")


@router.get("/faqs")
async def list_faqs(clinic_id: ClinicId):
    res = (
        supabase_admin()
        .table("faq_entries")
        .select("id,question,answer,category,created_at,updated_at")
        .eq("clinic_id", clinic_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


@router.post("/faqs", status_code=201)
async def create_faq(faq: FAQCreate, clinic_id: ClinicId):
    res = (
        supabase_admin()
        .table("faq_entries")
        .insert(
            {
                "clinic_id": clinic_id,
                "question": faq.question,
                "answer": faq.answer,
                "category": faq.category,
                "embedding": _embed(faq.question, faq.answer),
            }
        )
        .execute()
    )
    return res.data[0]


@router.put("/faqs/{faq_id}")
async def update_faq(faq_id: str, faq: FAQUpdate, clinic_id: ClinicId):
    update: dict = {}
    if faq.question is not None:
        update["question"] = faq.question
    if faq.answer is not None:
        update["answer"] = faq.answer
    if faq.category is not None:
        update["category"] = faq.category
    if not update:
        raise HTTPException(400, "No fields to update")

    if "question" in update or "answer" in update:
        existing = (
            supabase_admin()
            .table("faq_entries")
            .select("question,answer")
            .eq("id", faq_id)
            .eq("clinic_id", clinic_id)
            .single()
            .execute()
        )
        if not existing.data:
            raise HTTPException(404, "FAQ not found")
        new_q = update.get("question", existing.data["question"])
        new_a = update.get("answer", existing.data["answer"])
        update["embedding"] = _embed(new_q, new_a)

    res = (
        supabase_admin()
        .table("faq_entries")
        .update(update)
        .eq("id", faq_id)
        .eq("clinic_id", clinic_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "FAQ not found")
    return res.data[0]


@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: str, clinic_id: ClinicId):
    res = (
        supabase_admin()
        .table("faq_entries")
        .delete()
        .eq("id", faq_id)
        .eq("clinic_id", clinic_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "FAQ not found")
    return {"deleted": True, "id": faq_id}
