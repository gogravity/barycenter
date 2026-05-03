"""Unit tests for the pseudonymize primitive (TOOL-02)."""
import pytest


def test_pseudonymize_returns_sensitive_result(mock_kv_client):
    from barycenter.etl.primitives.pseudonymize import pseudonymize
    from barycenter.etl.primitives import PrimitiveResult
    result = pseudonymize("email", "alice@example.com", "12345", mock_kv_client)
    assert isinstance(result, PrimitiveResult)
    assert result.field_class == "SENSITIVE"
    assert result.expr == "?"


def test_pseudonymize_emits_pid_and_salt_version(mock_kv_client):
    from barycenter.etl.primitives.pseudonymize import pseudonymize
    result = pseudonymize("email", "alice@example.com", "12345", mock_kv_client)
    assert "email" in result.params
    assert "email_salt_version" in result.params
    assert len(result.params["email"]) == 64
    assert result.params["email_salt_version"] == "v1"


def test_pseudonymize_calls_kv(mock_kv_client):
    from barycenter.etl.primitives.pseudonymize import pseudonymize
    pseudonymize("email", "alice@example.com", "12345", mock_kv_client)
    mock_kv_client.get_secret.assert_called()
