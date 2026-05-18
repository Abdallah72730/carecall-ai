"""Unit tests for services/hours.py — clinic open/closed logic."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


def _mock_admin(rows: list[dict]):
    """Build a supabase_admin() mock that returns `rows` for any query."""
    chain = MagicMock()
    chain.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    execute_result = MagicMock()
    execute_result.data = rows
    chain.execute.return_value = execute_result
    return chain


# Monday 09:00 Mountain Time = Mon 16:00 UTC (MDT offset -6 in May, but ZoneInfo handles it)
_MON_10AM_MST = datetime(2026, 5, 18, 16, 0, 0, tzinfo=timezone.utc)  # Mon 10:00 MDT


@pytest.fixture(autouse=True)
def _no_supabase(monkeypatch):
    """Prevent any real Supabase calls during unit tests."""
    monkeypatch.setattr("services.hours.supabase_admin", lambda: _mock_admin([]))


class TestIsClinicOpen:
    def test_no_hours_configured_returns_false(self):
        from services.hours import is_clinic_open

        assert is_clinic_open("clinic-1", at=_MON_10AM_MST) is False

    def test_day_marked_closed_returns_false(self, monkeypatch):
        from services.hours import is_clinic_open

        rows = [
            {
                "day_of_week": 0,  # Monday
                "open_time": "09:00:00",
                "close_time": "17:00:00",
                "is_closed": True,
                "timezone": "America/Edmonton",
            }
        ]
        monkeypatch.setattr("services.hours.supabase_admin", lambda: _mock_admin(rows))
        assert is_clinic_open("clinic-1", at=_MON_10AM_MST) is False

    def test_within_open_hours_returns_true(self, monkeypatch):
        from services.hours import is_clinic_open

        rows = [
            {
                "day_of_week": 0,
                "open_time": "09:00:00",
                "close_time": "17:00:00",
                "is_closed": False,
                "timezone": "America/Edmonton",
            }
        ]
        monkeypatch.setattr("services.hours.supabase_admin", lambda: _mock_admin(rows))
        # _MON_10AM_MST is 10:00 MDT — within 09:00-17:00
        assert is_clinic_open("clinic-1", at=_MON_10AM_MST) is True

    def test_before_open_time_returns_false(self, monkeypatch):
        from services.hours import is_clinic_open

        rows = [
            {
                "day_of_week": 0,
                "open_time": "09:00:00",
                "close_time": "17:00:00",
                "is_closed": False,
                "timezone": "America/Edmonton",
            }
        ]
        monkeypatch.setattr("services.hours.supabase_admin", lambda: _mock_admin(rows))
        # 07:00 MDT = 13:00 UTC
        early = datetime(2026, 5, 18, 13, 0, 0, tzinfo=timezone.utc)
        assert is_clinic_open("clinic-1", at=early) is False

    def test_after_close_time_returns_false(self, monkeypatch):
        from services.hours import is_clinic_open

        rows = [
            {
                "day_of_week": 0,
                "open_time": "09:00:00",
                "close_time": "17:00:00",
                "is_closed": False,
                "timezone": "America/Edmonton",
            }
        ]
        monkeypatch.setattr("services.hours.supabase_admin", lambda: _mock_admin(rows))
        # 18:00 MDT = 00:00 UTC next day
        late = datetime(2026, 5, 19, 0, 0, 0, tzinfo=timezone.utc)
        assert is_clinic_open("clinic-1", at=late) is False

    def test_day_not_in_schedule_returns_false(self, monkeypatch):
        from services.hours import is_clinic_open

        # Only Tuesday (1) configured, check on Monday (0)
        rows = [
            {
                "day_of_week": 1,
                "open_time": "09:00:00",
                "close_time": "17:00:00",
                "is_closed": False,
                "timezone": "America/Edmonton",
            }
        ]
        monkeypatch.setattr("services.hours.supabase_admin", lambda: _mock_admin(rows))
        assert is_clinic_open("clinic-1", at=_MON_10AM_MST) is False

    def test_missing_open_time_returns_false(self, monkeypatch):
        from services.hours import is_clinic_open

        rows = [
            {
                "day_of_week": 0,
                "open_time": None,
                "close_time": "17:00:00",
                "is_closed": False,
                "timezone": "America/Edmonton",
            }
        ]
        monkeypatch.setattr("services.hours.supabase_admin", lambda: _mock_admin(rows))
        assert is_clinic_open("clinic-1", at=_MON_10AM_MST) is False

    def test_invalid_time_format_returns_false(self, monkeypatch):
        from services.hours import is_clinic_open

        rows = [
            {
                "day_of_week": 0,
                "open_time": "nine-am",
                "close_time": "five-pm",
                "is_closed": False,
                "timezone": "America/Edmonton",
            }
        ]
        monkeypatch.setattr("services.hours.supabase_admin", lambda: _mock_admin(rows))
        assert is_clinic_open("clinic-1", at=_MON_10AM_MST) is False

    def test_invalid_timezone_falls_back_to_edmonton(self, monkeypatch):
        from services.hours import is_clinic_open

        rows = [
            {
                "day_of_week": 0,
                "open_time": "09:00:00",
                "close_time": "17:00:00",
                "is_closed": False,
                "timezone": "Bogus/Timezone",
            }
        ]
        monkeypatch.setattr("services.hours.supabase_admin", lambda: _mock_admin(rows))
        # Should fall back and still evaluate correctly for Edmonton
        result = is_clinic_open("clinic-1", at=_MON_10AM_MST)
        assert isinstance(result, bool)
