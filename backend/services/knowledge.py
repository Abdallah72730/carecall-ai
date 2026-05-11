"""FAQ knowledge-base lookup."""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Any

from db import supabase_admin
from services.embedding import get_embedding

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 3
DISTANCE_THRESHOLD = 0.65  # cosine distance; lower = more similar

# Per-call embedding on Railway's shared CPU takes ~14s — way over the
# Vapi response budget. With ≤30 FAQs per clinic we just send the whole
# knowledge base in the system prompt and let the LLM pick the right
# answer. search_faqs is still available for future high-FAQ-count
# clinics; just route past it from the live path.
FAQ_CACHE_TTL_SEC = 300


@lru_cache(maxsize=128)
def _all_faqs_cached(clinic_id: str, time_bucket: int) -> tuple[tuple[str, str, str], ...]:
    try:
        res = (
            supabase_admin()
            .table("faq_entries")
            .select("question,answer,category")
            .eq("clinic_id", clinic_id)
            .order("category")
            .execute()
        )
    except Exception as exc:
        logger.warning("get_all_faqs failed for clinic=%s: %s", clinic_id, exc)
        return tuple()
    rows = res.data or []
    return tuple(
        (r.get("question") or "", r.get("answer") or "", r.get("category") or "")
        for r in rows
    )


def get_all_faqs(clinic_id: str) -> list[dict[str, str]]:
    """Return every FAQ for the clinic, cached for FAQ_CACHE_TTL_SEC.

    Used by the LLM proxy to inline the whole KB into the system prompt
    on every turn — avoids the ~14s per-call embedding cost on shared
    CPU. FAQ create/update flows still embed on write so we can switch
    back to vector search later without re-seeding.
    """
    bucket = int(time.time() // FAQ_CACHE_TTL_SEC)
    rows = _all_faqs_cached(clinic_id, bucket)
    return [{"question": q, "answer": a, "category": c} for (q, a, c) in rows]


def format_all_faqs(faqs: list[dict[str, str]]) -> str:
    """Render every FAQ as a numbered list grouped by category."""
    if not faqs:
        return ""
    by_cat: dict[str, list[dict[str, str]]] = {}
    for f in faqs:
        by_cat.setdefault(f.get("category") or "general", []).append(f)
    blocks: list[str] = []
    for cat in sorted(by_cat):
        lines = [f"[{cat}]"]
        for f in by_cat[cat]:
            lines.append(f"Q: {f['question']}\nA: {f['answer']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def search_faqs(clinic_id: str, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
    """Return up to top_k FAQs ranked by cosine similarity to the query."""
    if not query.strip():
        return []
    query_embedding = get_embedding(query)
    try:
        result = supabase_admin().rpc(
            "search_faqs",
            {
                "p_clinic_id": clinic_id,
                "p_query_embedding": query_embedding,
                "p_match_count": top_k,
            },
        ).execute()
    except Exception as exc:
        logger.warning("FAQ RPC failed for clinic=%s: %s", clinic_id, exc)
        return []
    return [r for r in (result.data or []) if r.get("distance", 1.0) <= DISTANCE_THRESHOLD]


def format_context(faqs: list[dict[str, Any]]) -> str:
    """Render top FAQs as a short context block for the assistant."""
    if not faqs:
        return ""
    lines = []
    for f in faqs:
        lines.append(f"Q: {f['question']}\nA: {f['answer']}")
    return "\n\n".join(lines)
