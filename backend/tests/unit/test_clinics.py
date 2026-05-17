"""Unit tests for services/clinics.py — clinic lookup and subscription logic."""
from __future__ import annotations

from unittest.mock import MagicMock


def _mock_admin(rows: list[dict]):
    chain = MagicMock()
    chain.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    result = MagicMock()
    result.data = rows
    chain.execute.return_value = result
    return chain


class TestClinicIdForAssistant:
    def test_none_returns_none(self):
        from services.clinics import clinic_id_for_assistant

        assert clinic_id_for_assistant(None) is None

    def test_empty_string_returns_none(self):
        from services.clinics import clinic_id_for_assistant

        assert clinic_id_for_assistant("") is None


class TestIsClinicLive:
    def test_db_exception_fails_open(self, monkeypatch):
        """Transient DB errors must not silently drop live calls."""
        from services.clinics import is_clinic_live

        failing = MagicMock()
        failing.table.side_effect = Exception("connection timeout")
        monkeypatch.setattr("services.clinics.supabase_admin", lambda: failing)
        assert is_clinic_live("clinic-abc") is True

    def test_no_row_returns_false(self, monkeypatch):
        from services.clinics import is_clinic_live

        monkeypatch.setattr(
            "services.clinics.supabase_admin", lambda: _mock_admin([])
        )
        assert is_clinic_live("clinic-abc") is False

    def test_inactive_clinic_returns_false(self, monkeypatch):
        from services.clinics import is_clinic_live

        monkeypatch.setattr(
            "services.clinics.supabase_admin",
            lambda: _mock_admin([{"subscription_status": "active", "is_active": False}]),
        )
        assert is_clinic_live("clinic-abc") is False

    def test_active_subscription_returns_true(self, monkeypatch):
        from services.clinics import is_clinic_live

        for status in ("trial", "trialing", "active", "pilot", "starter", "past_due"):
            monkeypatch.setattr(
                "services.clinics.supabase_admin",
                lambda: _mock_admin([{"subscription_status": status, "is_active": True}]),
            )
            assert is_clinic_live("clinic-abc") is True, f"Expected live for status={status}"

    def test_cancelled_subscription_returns_false(self, monkeypatch):
        from services.clinics import is_clinic_live

        monkeypatch.setattr(
            "services.clinics.supabase_admin",
            lambda: _mock_admin([{"subscription_status": "canceled", "is_active": True}]),
        )
        assert is_clinic_live("clinic-abc") is False

    def test_null_status_defaults_to_trial(self, monkeypatch):
        """A null subscription_status should be treated as trial (live)."""
        from services.clinics import is_clinic_live

        monkeypatch.setattr(
            "services.clinics.supabase_admin",
            lambda: _mock_admin([{"subscription_status": None, "is_active": True}]),
        )
        assert is_clinic_live("clinic-abc") is True


class TestGetTransferNumber:
    def test_returns_number_when_set(self, monkeypatch):
        from services.clinics import get_transfer_number

        monkeypatch.setattr(
            "services.clinics.supabase_admin",
            lambda: _mock_admin([{"transfer_number": "+15551234567"}]),
        )
        assert get_transfer_number("clinic-abc") == "+15551234567"

    def test_whitespace_only_returns_none(self, monkeypatch):
        from services.clinics import get_transfer_number

        monkeypatch.setattr(
            "services.clinics.supabase_admin",
            lambda: _mock_admin([{"transfer_number": "   "}]),
        )
        assert get_transfer_number("clinic-abc") is None

    def test_none_value_returns_none(self, monkeypatch):
        from services.clinics import get_transfer_number

        monkeypatch.setattr(
            "services.clinics.supabase_admin",
            lambda: _mock_admin([{"transfer_number": None}]),
        )
        assert get_transfer_number("clinic-abc") is None

    def test_no_row_returns_none(self, monkeypatch):
        from services.clinics import get_transfer_number

        monkeypatch.setattr(
            "services.clinics.supabase_admin", lambda: _mock_admin([])
        )
        assert get_transfer_number("clinic-abc") is None

    def test_exception_returns_none(self, monkeypatch):
        from services.clinics import get_transfer_number

        failing = MagicMock()
        failing.table.side_effect = Exception("db error")
        monkeypatch.setattr("services.clinics.supabase_admin", lambda: failing)
        assert get_transfer_number("clinic-abc") is None
