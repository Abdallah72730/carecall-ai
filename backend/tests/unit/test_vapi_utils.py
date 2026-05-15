"""Unit tests for pure helper functions in routers/vapi.py."""
from __future__ import annotations

from datetime import datetime

from routers.vapi import _clean, _last_user_text, _parse_iso


class TestLastUserText:
    def test_returns_last_user_message(self):
        messages = [
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "What are your hours?"},
            {"role": "assistant", "content": "We open at 9am."},
            {"role": "user", "content": "On weekends too?"},
        ]
        assert _last_user_text(messages) == "On weekends too?"

    def test_list_content_joined(self):
        messages = [
            {"role": "user", "content": [{"text": "Hello"}, {"text": " there"}]}
        ]
        assert _last_user_text(messages) == "Hello  there"

    def test_no_user_message_returns_empty(self):
        messages = [{"role": "assistant", "content": "Hi"}]
        assert _last_user_text(messages) == ""

    def test_empty_messages(self):
        assert _last_user_text([]) == ""


class TestClean:
    def test_strips_whitespace(self):
        assert _clean("  hello  ") == "hello"

    def test_none_returns_empty(self):
        assert _clean(None) == ""

    def test_non_string_converted(self):
        assert _clean(42) == "42"


class TestParseIso:
    def test_none_returns_none(self):
        assert _parse_iso(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_iso("") is None

    def test_valid_z_suffix(self):
        dt = _parse_iso("2024-01-15T10:30:00Z")
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None
        assert dt.year == 2024

    def test_valid_offset(self):
        dt = _parse_iso("2024-06-01T14:00:00+07:00")
        assert isinstance(dt, datetime)

    def test_invalid_string_returns_none(self):
        assert _parse_iso("not-a-date") is None
