"""Unit tests for services/notify.py — Telegram notification helper."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestSendTelegram:
    def test_no_token_returns_false(self, monkeypatch):
        import services.notify as notify_mod

        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_CHAT_ID", "123")
        assert notify_mod.send_telegram("hello") is False

    def test_no_chat_id_returns_false(self, monkeypatch):
        import services.notify as notify_mod

        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_CHAT_ID", "")
        assert notify_mod.send_telegram("hello") is False

    def test_200_response_returns_true(self, monkeypatch):
        import services.notify as notify_mod

        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_BOT_TOKEN", "bot123")
        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_CHAT_ID", "chat456")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("services.notify.httpx.post", return_value=mock_resp) as mock_post:
            result = notify_mod.send_telegram("Test message")
        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "bot123" in call_kwargs.args[0]

    def test_non_200_response_returns_false(self, monkeypatch):
        import services.notify as notify_mod

        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_BOT_TOKEN", "bot123")
        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_CHAT_ID", "chat456")

        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        with patch("services.notify.httpx.post", return_value=mock_resp):
            result = notify_mod.send_telegram("Test message")
        assert result is False

    def test_network_exception_returns_false(self, monkeypatch):
        import services.notify as notify_mod

        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_BOT_TOKEN", "bot123")
        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_CHAT_ID", "chat456")

        with patch("services.notify.httpx.post", side_effect=Exception("timeout")):
            result = notify_mod.send_telegram("Test message")
        assert result is False

    def test_message_included_in_payload(self, monkeypatch):
        import services.notify as notify_mod

        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_BOT_TOKEN", "bot")
        monkeypatch.setattr(notify_mod.settings, "TELEGRAM_CHAT_ID", "42")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("services.notify.httpx.post", return_value=mock_resp) as mock_post:
            notify_mod.send_telegram("New call from patient")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["text"] == "New call from patient"
        assert payload["chat_id"] == "42"
