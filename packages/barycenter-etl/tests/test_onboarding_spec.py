"""TOOL-01: tool onboarding spec template existence + section coverage."""
import pathlib


def test_onboarding_spec_template_exists():
    p = pathlib.Path("compliance/tool-onboarding-spec.template.md")
    assert p.exists()
    text = p.read_text()
    for section in ["Field Map", "Raw Schema", "ETL Recipe",
                    "AI-Zone Contributions", "Retention", "Erasure"]:
        assert section in text, f"missing section: {section}"
