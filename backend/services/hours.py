"""Clinic open/closed checks for after-hours routing."""
from __future__ import annotations

import logging
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from db import supabase_admin

logger = logging.getLogger(__name__)
DEFAULT_TZ = "America/Edmonton"


def is_clinic_open(clinic_id: str, at: datetime | None = None) -> bool:
    """Return True if the clinic is currently within open hours.

    Falls back to closed (False) when no hours are configured — safer for
    after-hours capture than assuming always-open.
    """
    rows = (
        supabase_admin()
        .table("clinic_hours")
        .select("day_of_week,open_time,close_time,is_closed,timezone")
        .eq("clinic_id", clinic_id)
        .execute()
    ).data or []
    if not rows:
        return False

    by_dow = {r["day_of_week"]: r for r in rows}
    tz_name = rows[0].get("timezone") or DEFAULT_TZ
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo(DEFAULT_TZ)

    now_local = (at or datetime.now(timezone.utc)).astimezone(tz)
    today = by_dow.get(now_local.weekday())
    if not today or today.get("is_closed"):
        return False

    open_str = today.get("open_time")
    close_str = today.get("close_time")
    if not open_str or not close_str:
        return False
    try:
        open_t = time.fromisoformat(open_str)
        close_t = time.fromisoformat(close_str)
    except ValueError:
        return False
    return open_t <= now_local.time() <= close_t


def get_day_hours(clinic_id: str, day_of_week: int) -> dict | None:
    res = (
        supabase_admin()
        .table("clinic_hours")
        .select("*")
        .eq("clinic_id", clinic_id)
        .eq("day_of_week", day_of_week)
        .limit(1)
        .execute()
    ).data
    return res[0] if res else None


def get_clinic_for_email(clinic_id: str) -> dict | None:
    res = (
        supabase_admin()
        .table("clinics")
        .select("name,email")
        .eq("id", clinic_id)
        .limit(1)
        .execute()
    ).data
    return res[0] if res else None
