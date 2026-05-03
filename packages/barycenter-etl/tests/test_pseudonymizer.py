"""Unit tests for the Pseudonymizer (ENC-02)."""
import pytest

pytest.importorskip("barycenter.etl.framework.pseudonymizer", reason="Plan 02 implements")


def test_pseudonymize_returns_pid_and_version(mock_kv_client):
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer
    p = Pseudonymizer(mock_kv_client)
    pid, ver = p.derive("alice@example.com", "12345")
    assert len(pid) == 64  # SHA-256 hex
    assert ver == "v1"
    # Salt must have been fetched via KV (never module-level)
    mock_kv_client.get_secret.assert_called_once()


def test_pseudonymize_lowercases_email(mock_kv_client):
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer
    p = Pseudonymizer(mock_kv_client)
    pid_lower, _ = p.derive("alice@example.com", "12345")
    pid_upper, _ = p.derive("ALICE@EXAMPLE.COM", "12345")
    assert pid_lower == pid_upper
