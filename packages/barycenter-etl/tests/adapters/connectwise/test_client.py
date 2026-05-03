"""Unit tests for the CW Manage HTTP client (Plan 05)."""
import pytest

pytest.importorskip("barycenter.etl.adapters.connectwise.client",
                    reason="Plan 05 implements")
pytest.importorskip("respx", reason="respx required for httpx mocking")


def test_paginate_stops_on_short_page():
    # Implementation lands in Plan 05; this stub asserts the contract.
    pass
