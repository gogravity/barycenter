"""End-to-end integration test (Plan 05): mocked CW -> primitives -> raw_cw -> ai_zone."""
import pytest

pytest.importorskip("barycenter.etl.adapters.connectwise.adapter",
                    reason="Plan 05 implements end-to-end")


@pytest.mark.integration
def test_e2e_cw_to_raw_to_ai_zone():
    # End-to-end: mocked CW -> primitives -> MERGE -> ShapeBuilder -> ai_zone
    # Implemented in Plan 05.
    pass
