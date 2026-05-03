"""Unit tests for the salt rotation framework (ENC-02)."""
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def versioned_kv():
    """KV mock that returns distinct salt material per version."""
    kv = MagicMock(name="kv_client")

    def _get(name, version=None):
        secret = MagicMock()
        # value differs by version → distinct pids
        secret.value = f"salt-bytes-for-{version or 'latest'}"
        secret.properties.version = version or "latest"
        return secret

    kv.get_secret.side_effect = _get
    return kv


def test_dual_write_window_emits_both_versions(versioned_kv, mock_sql, mock_audit, tmp_path):
    from barycenter.etl.framework.salt_rotation import SaltRotation
    state_path = tmp_path / "salt-rotation-state.yaml"
    state_path.write_text("version: 1\ntenants: {}\n")
    sr = SaltRotation(versioned_kv, mock_sql, mock_audit,
                      state_path=str(state_path))
    result = sr.dual_write("alice@example.com", "12345",
                           old_version="v1", new_version="v2")
    assert result.pid_old != result.pid_new
    assert result.salt_version_old == "v1"
    assert result.salt_version_new == "v2"
    # Two dual_write audit events emitted (one per version)
    dual_writes = [c for c in mock_audit.emit.call_args_list
                   if c.args[0].verb == "salt.rotate.dual_write"]
    assert len(dual_writes) == 2


def test_open_window_writes_state_and_audits(versioned_kv, mock_sql, mock_audit, tmp_path):
    from barycenter.etl.framework.salt_rotation import SaltRotation
    state_path = tmp_path / "salt-rotation-state.yaml"
    state_path.write_text("version: 1\ntenants: {}\n")
    sr = SaltRotation(versioned_kv, mock_sql, mock_audit,
                      state_path=str(state_path))
    sr.open_window("12345", old_version="v1", new_version="v2")
    import yaml
    doc = yaml.safe_load(state_path.read_text())
    assert doc["tenants"]["12345"]["mode"] == "dual-write"
    assert doc["tenants"]["12345"]["old_version"] == "v1"
    assert doc["tenants"]["12345"]["new_version"] == "v2"
    open_events = [c for c in mock_audit.emit.call_args_list
                   if c.args[0].verb == "salt.rotate.open_window"]
    assert open_events


def test_cut_over_flips_mode(versioned_kv, mock_sql, mock_audit, tmp_path):
    from barycenter.etl.framework.salt_rotation import SaltRotation
    state_path = tmp_path / "salt-rotation-state.yaml"
    state_path.write_text("version: 1\ntenants: {}\n")
    sr = SaltRotation(versioned_kv, mock_sql, mock_audit,
                      state_path=str(state_path))
    sr.open_window("12345", old_version="v1", new_version="v2")
    sr.cut_over("12345")
    import yaml
    doc = yaml.safe_load(state_path.read_text())
    assert doc["tenants"]["12345"]["mode"] == "new-only"
    cut_events = [c for c in mock_audit.emit.call_args_list
                  if c.args[0].verb == "salt.rotate.cut_over"]
    assert cut_events


def test_cut_over_without_window_raises(versioned_kv, mock_sql, mock_audit, tmp_path):
    from barycenter.etl.framework.salt_rotation import SaltRotation
    state_path = tmp_path / "salt-rotation-state.yaml"
    state_path.write_text("version: 1\ntenants: {}\n")
    sr = SaltRotation(versioned_kv, mock_sql, mock_audit,
                      state_path=str(state_path))
    with pytest.raises(ValueError, match="no rotation window"):
        sr.cut_over("never-opened")


def test_dual_write_result_is_dataclass():
    from barycenter.etl.framework.salt_rotation import DualWriteResult
    import dataclasses
    assert dataclasses.is_dataclass(DualWriteResult)
    r = DualWriteResult(pid_old="a", pid_new="b",
                        salt_version_old="v1", salt_version_new="v2")
    assert r.pid_old == "a" and r.pid_new == "b"
