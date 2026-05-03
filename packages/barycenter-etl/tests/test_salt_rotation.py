"""Unit tests for the salt rotation framework (ENC-02)."""
import pytest

pytest.importorskip("barycenter.etl.framework.salt_rotation", reason="Plan 04 implements")


def test_dual_write_window_emits_both_versions(mock_kv_client, mock_sql, mock_audit):
    from barycenter.etl.framework.salt_rotation import SaltRotation
    sr = SaltRotation(mock_kv_client, mock_sql, mock_audit)
    result = sr.dual_write("alice@example.com", "12345",
                           old_version="v1", new_version="v2")
    assert result.pid_old != result.pid_new
    assert result.salt_version_old == "v1" and result.salt_version_new == "v2"
