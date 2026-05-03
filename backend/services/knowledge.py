"""FAQ knowledge-base lookup over pgvector."""
from __future__ import annotations

import logging
from typing import Any

from db import supabase_admin
from services.embedding import get_embedding

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 3
DISTANCE_THRESHOLD = 0.65  # cosine distance; lower = more similar


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
