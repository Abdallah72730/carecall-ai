"""Supabase client singletons."""
from __future__ import annotations

from supabase import Client, create_client

from config import require


_admin: Client | None = None


def supabase_admin() -> Client:
    """Service-role client. Bypasses RLS — use only in trusted server code."""
    global _admin
    if _admin is None:
        _admin = create_client(
            require("SUPABASE_URL"),
            require("SUPABASE_SERVICE_ROLE_KEY"),
        )
    return _admin
