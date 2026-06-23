"""Unit tests: OutreachForgeAgent.

All tests mock Supabase and Claude. No live API calls.
Run: PYTHONPATH=. python3 -m pytest tests/test_outreach_agent.py -v
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.outreach import MigrationNotRunError, OutreachForgeAgent
from models import LLMError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_lead(**overrides) -> dict:
    base = {
        "name": "Rahul Sharma",
        "handle": "@rahul_dev",
        "platform": "x",
        "fit_context": "Freelance developer, tweeted about losing Rs80k from a client who never signed a contract",
    }
    base.update(overrides)
    return base


def _mock_supabase() -> MagicMock:
    client = MagicMock()
    ok = MagicMock()
    ok.error = None
    ok.data = [{"id": "uuid-1", "status": "drafted"}]
    client.table.return_value.insert.return_value.execute.return_value = ok
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = ok
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = ok
    return client


def _mock_claude_resp(text: str = "Draft outreach message") -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# TestDraftMessage
# ---------------------------------------------------------------------------

class TestDraftMessage:
    def test_missing_name_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        with pytest.raises(ValueError, match="name"):
            OutreachForgeAgent().draft_message({"platform": "x", "fit_context": "ctx"})

    def test_missing_platform_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        with pytest.raises(ValueError, match="platform"):
            OutreachForgeAgent().draft_message({"name": "Rahul", "fit_context": "ctx"})

    def test_missing_fit_context_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        with pytest.raises(ValueError, match="fit_context"):
            OutreachForgeAgent().draft_message({"name": "Rahul", "platform": "x"})

    def test_empty_name_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        with pytest.raises(ValueError):
            OutreachForgeAgent().draft_message(_valid_lead(name=""))

    def test_missing_api_key_raises_llm_error(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(LLMError):
            OutreachForgeAgent().draft_message(_valid_lead())

    def test_returns_stripped_string(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        with patch("llm.claude.ClaudeClient.complete", return_value=_mock_claude_resp("  Saw your tweet.  ")):
            result = OutreachForgeAgent().draft_message(_valid_lead())
        assert result == "Saw your tweet."

    def test_handle_is_optional(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        with patch("llm.claude.ClaudeClient.complete", return_value=_mock_claude_resp("Draft")):
            lead = _valid_lead()
            lead.pop("handle")
            result = OutreachForgeAgent().draft_message(lead)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# TestQueueForApproval
# ---------------------------------------------------------------------------

class TestQueueForApproval:
    def test_inserts_with_status_drafted(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().queue_for_approval(_valid_lead(), "First-touch message")
        payload = mock_client.table.return_value.insert.call_args[0][0]
        assert payload["status"] == "drafted"

    def test_payload_contains_lead_fields(self):
        mock_client = _mock_supabase()
        lead = _valid_lead()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().queue_for_approval(lead, "Draft text")
        payload = mock_client.table.return_value.insert.call_args[0][0]
        assert payload["name"] == lead["name"]
        assert payload["platform"] == lead["platform"]
        assert payload["draft_message"] == "Draft text"

    def test_status_never_sent_or_approved(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().queue_for_approval(_valid_lead(), "Draft")
        payload = mock_client.table.return_value.insert.call_args[0][0]
        assert payload["status"] == "drafted"
        assert payload.get("sent_at") is None
        assert payload.get("approved_at") is None

    def test_inserts_into_outreach_leads_table(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().queue_for_approval(_valid_lead(), "Draft")
        mock_client.table.assert_called_with("outreach_leads")

    def test_supabase_error_raises_runtime_error(self):
        mock_client = MagicMock()
        err = MagicMock()
        err.error = "connection refused"
        mock_client.table.return_value.insert.return_value.execute.return_value = err
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Supabase insert failed"):
                OutreachForgeAgent().queue_for_approval(_valid_lead(), "Draft")


# ---------------------------------------------------------------------------
# TestGetPendingApprovals
# ---------------------------------------------------------------------------

class TestGetPendingApprovals:
    def test_returns_list(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            result = OutreachForgeAgent().get_pending_approvals()
        assert isinstance(result, list)

    def test_queries_status_drafted(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().get_pending_approvals()
        eq_args = mock_client.table.return_value.select.return_value.eq.call_args[0]
        assert eq_args == ("status", "drafted")

    def test_queries_outreach_leads_table(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().get_pending_approvals()
        mock_client.table.assert_called_with("outreach_leads")

    def test_returns_empty_list_when_data_is_none(self):
        mock_client = MagicMock()
        empty = MagicMock()
        empty.data = None
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = empty
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            result = OutreachForgeAgent().get_pending_approvals()
        assert result == []


# ---------------------------------------------------------------------------
# TestMarkApproved
# ---------------------------------------------------------------------------

class TestMarkApproved:
    def test_sets_status_approved(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().mark_approved("lead-uuid-001")
        payload = mock_client.table.return_value.update.call_args[0][0]
        assert payload["status"] == "approved"

    def test_sets_approved_at(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().mark_approved("lead-uuid-001")
        payload = mock_client.table.return_value.update.call_args[0][0]
        assert "approved_at" in payload and payload["approved_at"] is not None

    def test_filters_by_id(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().mark_approved("target-id")
        eq_args = mock_client.table.return_value.update.return_value.eq.call_args[0]
        assert eq_args == ("id", "target-id")

    def test_does_not_set_sent_at(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().mark_approved("lead-uuid-001")
        payload = mock_client.table.return_value.update.call_args[0][0]
        assert "sent_at" not in payload

    def test_supabase_error_raises_runtime_error(self):
        mock_client = MagicMock()
        err = MagicMock()
        err.error = "row not found"
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = err
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Supabase update failed"):
                OutreachForgeAgent().mark_approved("bad-id")


# ---------------------------------------------------------------------------
# TestMarkSent
# ---------------------------------------------------------------------------

class TestMarkSent:
    def test_sets_status_sent(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().mark_sent("lead-uuid-002")
        payload = mock_client.table.return_value.update.call_args[0][0]
        assert payload["status"] == "sent"

    def test_sets_sent_at(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().mark_sent("lead-uuid-002")
        payload = mock_client.table.return_value.update.call_args[0][0]
        assert "sent_at" in payload and payload["sent_at"] is not None

    def test_filters_by_id(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().mark_sent("target-sent-id")
        eq_args = mock_client.table.return_value.update.return_value.eq.call_args[0]
        assert eq_args == ("id", "target-sent-id")

    def test_does_not_set_approved_at(self):
        mock_client = _mock_supabase()
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            OutreachForgeAgent().mark_sent("lead-uuid-002")
        payload = mock_client.table.return_value.update.call_args[0][0]
        assert "approved_at" not in payload

    def test_supabase_error_raises_runtime_error(self):
        mock_client = MagicMock()
        err = MagicMock()
        err.error = "network error"
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = err
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Supabase update failed"):
                OutreachForgeAgent().mark_sent("bad-id")


# ---------------------------------------------------------------------------
# TestSupabaseClient
# ---------------------------------------------------------------------------

class TestSupabaseClient:
    def test_missing_url_raises_runtime_error(self, monkeypatch):
        import sys
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-key")
        monkeypatch.setitem(sys.modules, "supabase", MagicMock())
        with pytest.raises(RuntimeError, match="SUPABASE_URL"):
            OutreachForgeAgent._supabase_client()

    def test_missing_service_role_key_raises_runtime_error(self, monkeypatch):
        import sys
        monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        monkeypatch.setitem(sys.modules, "supabase", MagicMock())
        with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_ROLE_KEY"):
            OutreachForgeAgent._supabase_client()


# ---------------------------------------------------------------------------
# TestVerifyMigration
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# TestSendApprovalNotification
# ---------------------------------------------------------------------------

class TestSendApprovalNotification:
    def test_send_approval_notification_success(self, monkeypatch):
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/fake")
        mock_resp = MagicMock(status_code=204)
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        with patch("agents.outreach.httpx.AsyncClient", return_value=mock_http):
            result = asyncio.run(
                OutreachForgeAgent().send_approval_notification("id-1", "Rahul Sharma", "Draft")
            )
        assert result is True

    def test_send_approval_notification_missing_env(self, monkeypatch):
        monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
        result = asyncio.run(
            OutreachForgeAgent().send_approval_notification("id-1", "Rahul Sharma", "Draft")
        )
        assert result is False

    def test_queue_for_approval_triggers_discord_notification(self):
        mock_sb = _mock_supabase()
        ok_with_id = MagicMock()
        ok_with_id.error = None
        ok_with_id.data = [{"id": "lead-abc-123"}]
        mock_sb.table.return_value.insert.return_value.execute.return_value = ok_with_id
        mock_notify = AsyncMock(return_value=True)
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_sb):
            with patch.object(OutreachForgeAgent, "send_approval_notification", mock_notify):
                OutreachForgeAgent().queue_for_approval(_valid_lead(), "Draft text")
        mock_notify.assert_called_once_with("lead-abc-123", "Rahul Sharma", "Draft text")


class TestVerifyMigration:
    def test_verify_migration_raises_on_missing_table(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = (
            Exception("relation \"outreach_leads\" does not exist")
        )
        with patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client):
            with pytest.raises(MigrationNotRunError, match="outreach_leads"):
                OutreachForgeAgent().verify_migration()
