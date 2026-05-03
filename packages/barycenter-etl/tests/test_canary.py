"""Unit tests for the multi-field CUI canary scanner (COMP-07)."""
import pytest

pytest.importorskip("barycenter.etl.framework.canary", reason="Plan 04 implements")


def test_canary_detects_phrase_in_text():
    from barycenter.etl.framework.canary import CanaryScanner
    s = CanaryScanner("compliance/cui-canary-phrases.yaml")
    assert s.scan_text("This contains FOUO content")
    assert s.scan_subject("FEDCON ticket")
    assert s.scan_filename("CUI_doc.pdf")


def test_attachment_refused_for_cui_tenant():
    from barycenter.etl.framework.canary import CanaryScanner
    s = CanaryScanner("compliance/cui-canary-phrases.yaml")
    assert s.refuse_attachment(tenant_cui_flag=True)
    assert not s.refuse_attachment(tenant_cui_flag=False)
