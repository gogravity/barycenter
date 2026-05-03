"""Unit tests for the pseudonymize primitive (TOOL-02)."""
import pytest

pytest.importorskip("barycenter.etl.primitives.pseudonymize",
                    reason="Plan 02 implements primitives")


def test_pseudonymize_returns_primitive_result(mock_kv_client):
    from barycenter.etl.primitives.pseudonymize import pseudonymize
    from barycenter.etl.primitives import PrimitiveResult
    result = pseudonymize(
        "email", "alice@example.com", "12345", mock_kv_client
    )
    assert isinstance(result, PrimitiveResult)
    assert result.field_class == "SENSITIVE"
