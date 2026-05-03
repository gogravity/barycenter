"""Shared pytest fixtures for barycenter-etl."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_sql():
    conn = MagicMock(name="sql_conn")
    cur = MagicMock(name="cursor")
    conn.cursor.return_value = cur
    return conn


@pytest.fixture
def mock_kv_client():
    kv = MagicMock(name="kv_client")
    # Default: any get_secret returns a versioned secret with deterministic value
    secret = MagicMock(name="secret")
    secret.value = "0" * 64  # 32-byte hex salt
    secret.properties.version = "v1"
    kv.get_secret.return_value = secret
    return kv


@pytest.fixture
def mock_audit():
    audit = MagicMock(name="audit_client")
    # emit() must be allowed to raise in fail-closed tests; default returns None
    audit.emit.return_value = None
    return audit


@pytest.fixture
def mock_cw_client():
    client = MagicMock(name="cw_client")
    client.paginate.return_value = iter([])
    return client


@pytest.fixture
def synthetic_cw_company():
    return {
        "id": 12345,
        "name": "Acme Inc",
        "addressLine1": "1 Main St",
        "city": "Springfield",
        "state": "IL",
        "types": [{"name": "Commercial"}],
        "customFields": {"ai_opt_out": False},
        "_info": {"lastUpdated": "2026-05-01T00:00:00Z"},
        "notes": "internal-only notes that must be dropped",
    }


@pytest.fixture
def synthetic_cui_company():
    return {
        "id": 99999,
        "name": "DefenseCorp",
        "types": [{"name": "Defense"}, {"name": "Federal"}],
        "customFields": {"cui_handling_required": True, "ai_opt_out": True},
        "_info": {"lastUpdated": "2026-05-01T00:00:00Z"},
    }


@pytest.fixture
def synthetic_cui_ticket_with_canary():
    return {
        "id": 5001,
        "company": {"id": 99999},
        "summary": "Investigate FOUO marking on shipment",  # canary in subject
        "status": {"name": "Open"},
        "priority": {"name": "High"},
        "type": {"name": "Incident"},
        "_info": {"dateEntered": "2026-05-01T00:00:00Z",
                  "lastUpdated": "2026-05-01T00:00:00Z"},
        "attachments": [{"filename": "CUI_briefing.pdf", "size": 2048,
                         "contentType": "application/pdf"}],
    }
