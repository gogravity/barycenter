#!/usr/bin/env python3
"""ENC-02 CI gate: verify salt rotation runbook + state YAML exist and are well-formed."""
from __future__ import annotations
import argparse
import sys
import pathlib
import tempfile
import yaml

RUNBOOK = pathlib.Path("compliance/salt-rotation-runbook.md")
STATE = pathlib.Path("compliance/salt-rotation-state.yaml")
REQUIRED_RUNBOOK_SECTIONS = [
    "Pre-flight", "Procedure", "Create new secret version",
    "dual-write", "Cut over", "Retire old version", "Audit", "Pass criteria"
]


def check_runbook(runbook: pathlib.Path) -> list[str]:
    errors: list[str] = []
    if not runbook.exists():
        return [f"missing: {runbook}"]
    text = runbook.read_text()
    for section in REQUIRED_RUNBOOK_SECTIONS:
        if section.lower() not in text.lower():
            errors.append(f"runbook missing section: {section}")
    return errors


def check_state(state: pathlib.Path) -> list[str]:
    errors: list[str] = []
    if not state.exists():
        return [f"missing: {state}"]
    try:
        doc = yaml.safe_load(state.read_text())
    except yaml.YAMLError as e:
        return [f"state YAML malformed: {e}"]
    if not isinstance(doc, dict):
        return ["state YAML root must be a mapping"]
    for key in ("version", "tenants", "executions", "fire_drill"):
        if key not in doc:
            errors.append(f"state YAML missing key: {key}")
    fd = doc.get("fire_drill", {})
    if not isinstance(fd, dict) or "completed" not in fd:
        errors.append("state YAML fire_drill must be a mapping with 'completed' field")
    return errors


def main() -> None:
    ap = argparse.ArgumentParser(description="ENC-02 salt-runbook gate")
    ap.add_argument("--check-static", action="store_true", default=True)
    ap.add_argument("--self-test", action="store_true",
                    help="Meta-test: inject missing runbook and assert gate fires")
    args = ap.parse_args()

    if args.self_test:
        with tempfile.TemporaryDirectory() as td:
            missing = pathlib.Path(td) / "nonexistent.md"
            errors = check_runbook(missing)
            if not errors:
                print("salt-runbook meta-test FAIL: gate did not fire on missing runbook",
                      file=sys.stderr)
                sys.exit(1)
            print("salt-runbook meta-test PASS")
            sys.exit(0)

    errors = check_runbook(RUNBOOK) + check_state(STATE)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    print(f"ENC-02 OK: runbook + state YAML present and well-formed")
    sys.exit(0)


if __name__ == "__main__":
    main()
