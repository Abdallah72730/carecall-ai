"""Unit tests for services/vapi_provision.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_supabase(clinic_row: dict | None):
    chain = MagicMock()
    chain.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.update.return_value = chain
    result = MagicMock()
    result.data = clinic_row
    chain.single.return_value = chain
    chain.execute.return_value = result
    return chain


class TestBasePayload:
    def test_contains_clinic_name(self):
        from services.vapi_provision import _base_payload

        p = _base_payload("Maple Dental")
        assert "Maple Dental" in p["name"]
        assert "Maple Dental" in p["firstMessage"]

    def test_system_message_has_disclosure(self):
        from services.vapi_provision import _base_payload

        p = _base_payload("ABC Clinic")
        system_content = p["model"]["messages"][0]["content"]
        assert "AI" in system_content

    def test_has_save_message_tool(self):
        from services.vapi_provision import _base_payload

        p = _base_payload("Test Clinic")
        tool_names = [t.get("function", {}).get("name") for t in p["model"]["tools"]]
        assert "save_message" in tool_names

    def test_model_provider_is_custom_llm(self):
        from services.vapi_provision import _base_payload

        p = _base_payload("X")
        assert p["model"]["provider"] == "custom-llm"

    def test_voice_provider_is_cartesia(self):
        from services.vapi_provision import _base_payload

        p = _base_payload("X")
        assert p["voice"]["provider"] == "cartesia"

    def test_transcriber_is_deepgram(self):
        from services.vapi_provision import _base_payload

        p = _base_payload("X")
        assert p["transcriber"]["provider"] == "deepgram"


class TestAttachTransferTool:
    def test_no_number_adds_nothing(self):
        from services.vapi_provision import _attach_transfer_tool

        payload = {"model": {"tools": []}}
        _attach_transfer_tool(payload, None)
        assert payload["model"]["tools"] == []

    def test_empty_string_adds_nothing(self):
        from services.vapi_provision import _attach_transfer_tool

        payload = {"model": {"tools": []}}
        _attach_transfer_tool(payload, "")
        assert payload["model"]["tools"] == []

    def test_adds_transfer_tool_with_number(self):
        from services.vapi_provision import _attach_transfer_tool

        payload = {"model": {"tools": []}}
        _attach_transfer_tool(payload, "+14031234567")
        assert len(payload["model"]["tools"]) == 1
        tool = payload["model"]["tools"][0]
        assert tool["type"] == "transferCall"
        assert tool["destinations"][0]["number"] == "+14031234567"

    def test_blind_transfer_mode(self):
        from services.vapi_provision import _attach_transfer_tool

        payload = {"model": {"tools": []}}
        _attach_transfer_tool(payload, "+14031234567")
        mode = payload["model"]["tools"][0]["destinations"][0]["transferPlan"]["mode"]
        assert mode == "blind-transfer"


class TestCreateAssistantForClinic:
    def test_returns_existing_assistant_without_api_call(self, monkeypatch):
        from services.vapi_provision import create_assistant_for_clinic

        clinic = {
            "id": "c1",
            "name": "Test Clinic",
            "vapi_assistant_id": "asst_existing",
            "transfer_number": None,
        }
        monkeypatch.setattr(
            "services.vapi_provision.supabase_admin",
            lambda: _make_supabase(clinic),
        )
        with patch("services.vapi_provision.httpx.post") as mock_post:
            result = create_assistant_for_clinic("c1")
        assert result == "asst_existing"
        mock_post.assert_not_called()

    def test_raises_on_missing_clinic(self, monkeypatch):
        from services.vapi_provision import create_assistant_for_clinic

        monkeypatch.setattr(
            "services.vapi_provision.supabase_admin",
            lambda: _make_supabase(None),
        )
        import pytest

        with pytest.raises(ValueError, match="not found"):
            create_assistant_for_clinic("missing-id")

    def test_creates_and_saves_new_assistant(self, monkeypatch):
        from services.vapi_provision import create_assistant_for_clinic

        clinic = {
            "id": "c2",
            "name": "New Clinic",
            "vapi_assistant_id": None,
            "transfer_number": None,
        }
        monkeypatch.setattr(
            "services.vapi_provision.supabase_admin",
            lambda: _make_supabase(clinic),
        )
        monkeypatch.setenv("VAPI_API_KEY", "test-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": "asst_new123"}

        with patch("services.vapi_provision.httpx.post", return_value=mock_resp):
            result = create_assistant_for_clinic("c2")

        assert result == "asst_new123"

    def test_raises_on_vapi_error(self, monkeypatch):
        from services.vapi_provision import create_assistant_for_clinic

        clinic = {
            "id": "c3",
            "name": "Fail Clinic",
            "vapi_assistant_id": None,
            "transfer_number": None,
        }
        monkeypatch.setattr(
            "services.vapi_provision.supabase_admin",
            lambda: _make_supabase(clinic),
        )
        monkeypatch.setenv("VAPI_API_KEY", "test-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.text = "Unprocessable Entity"

        import pytest

        with patch("services.vapi_provision.httpx.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="Vapi create-assistant failed"):
                create_assistant_for_clinic("c3")


class TestUpdateAssistantTransfer:
    def test_returns_false_when_no_assistant(self, monkeypatch):
        from services.vapi_provision import update_assistant_transfer

        clinic = {"vapi_assistant_id": None, "transfer_number": "+1000", "name": "X"}
        monkeypatch.setattr(
            "services.vapi_provision.supabase_admin",
            lambda: _make_supabase(clinic),
        )
        with patch("services.vapi_provision.httpx.patch") as mock_patch:
            result = update_assistant_transfer("c1")
        assert result is False
        mock_patch.assert_not_called()

    def test_returns_false_when_no_clinic_row(self, monkeypatch):
        from services.vapi_provision import update_assistant_transfer

        monkeypatch.setattr(
            "services.vapi_provision.supabase_admin",
            lambda: _make_supabase(None),
        )
        result = update_assistant_transfer("ghost")
        assert result is False

    def test_returns_true_on_success(self, monkeypatch):
        from services.vapi_provision import update_assistant_transfer

        clinic = {
            "vapi_assistant_id": "asst_abc",
            "transfer_number": "+14031234567",
            "name": "Maple Dental",
        }
        monkeypatch.setattr(
            "services.vapi_provision.supabase_admin",
            lambda: _make_supabase(clinic),
        )
        monkeypatch.setenv("VAPI_API_KEY", "test-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("services.vapi_provision.httpx.patch", return_value=mock_resp):
            result = update_assistant_transfer("c1")

        assert result is True

    def test_returns_false_on_vapi_error(self, monkeypatch):
        from services.vapi_provision import update_assistant_transfer

        clinic = {
            "vapi_assistant_id": "asst_abc",
            "transfer_number": "+14031234567",
            "name": "Maple Dental",
        }
        monkeypatch.setattr(
            "services.vapi_provision.supabase_admin",
            lambda: _make_supabase(clinic),
        )
        monkeypatch.setenv("VAPI_API_KEY", "test-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("services.vapi_provision.httpx.patch", return_value=mock_resp):
            result = update_assistant_transfer("c1")

        assert result is False
