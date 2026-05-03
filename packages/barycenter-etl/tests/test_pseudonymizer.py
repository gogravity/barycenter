"""Unit tests for the Pseudonymizer (ENC-02 / Pitfall 5)."""
import pytest


def test_pseudonymize_returns_pid_and_version(mock_kv_client):
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer
    p = Pseudonymizer(mock_kv_client)
    pid, ver = p.derive("alice@example.com", "12345")
    assert len(pid) == 64  # SHA-256 hex
    assert ver == "v1"
    # Salt must have been fetched via KV (never module-level cached)
    mock_kv_client.get_secret.assert_called_once()


def test_pseudonymize_lowercases_email(mock_kv_client):
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer
    p = Pseudonymizer(mock_kv_client)
    pid_lower, _ = p.derive("alice@example.com", "12345")
    pid_upper, _ = p.derive("ALICE@EXAMPLE.COM", "12345")
    assert pid_lower == pid_upper


def test_pseudonymize_fetches_salt_fresh_each_call(mock_kv_client):
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer
    p = Pseudonymizer(mock_kv_client)
    p.derive("alice@example.com", "12345")
    p.derive("alice@example.com", "12345")
    # Each call MUST hit Key Vault — no caching (Pitfall 5)
    assert mock_kv_client.get_secret.call_count == 2


def test_pseudonymize_uses_per_tenant_secret_name(mock_kv_client):
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer
    p = Pseudonymizer(mock_kv_client)
    p.derive("alice@example.com", "tenant-abc")
    args, kwargs = mock_kv_client.get_secret.call_args
    assert args[0] == "salt-tenant-abc"


def test_pseudonymize_repr_excludes_salt(mock_kv_client):
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer
    p = Pseudonymizer(mock_kv_client)
    # mock_kv_client.get_secret().value is "0" * 64 — must not appear in repr.
    assert "0" * 64 not in repr(p)
    assert "Pseudonymizer" in repr(p)


def test_pseudonymize_rejects_empty_email(mock_kv_client):
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer
    p = Pseudonymizer(mock_kv_client)
    with pytest.raises(ValueError):
        p.derive("", "12345")


def test_pseudonymize_rejects_empty_tenant(mock_kv_client):
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer
    p = Pseudonymizer(mock_kv_client)
    with pytest.raises(ValueError):
        p.derive("alice@example.com", "")
