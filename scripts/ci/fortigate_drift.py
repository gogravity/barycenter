"""NETW-02 CI gate: nightly diff of live FortiGate config against
infra/networking/fortigate-config/policies.json.

Uses FortiOS REST API (per RESEARCH §Don't Hand-Roll: do NOT parse `show` output).

Modes:
  --self-test:           load fixture identical to policies.json; exit 0.
  --self-test --drifted: load divergent fixture; exit nonzero  → reported as PASS.
  (default):             query live FortiGate via API token from KV.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

POLICIES_PATH = Path("infra/networking/fortigate-config/policies.json")


def _normalize(config: dict) -> dict:
    """Strip transient fields the FortiGate REST API returns but we don't manage
    (uuid, seq_num, _last_modified) so the diff is stable across runs."""
    out = json.loads(json.dumps(config))  # deep copy
    for p in out.get("policies", []):
        for transient in ("uuid", "seq_num", "_last_modified"):
            p.pop(transient, None)
    return out


def _diff(expected: dict, actual: dict) -> list[str]:
    errors: list[str] = []
    exp_policies = expected.get("policies", [])
    act_policies = actual.get("policies", [])
    exp_policy_names = {p["name"] for p in exp_policies}
    act_policy_names = {p["name"] for p in act_policies}
    missing = exp_policy_names - act_policy_names
    extra = act_policy_names - exp_policy_names
    if missing:
        errors.append(f"NETW-02: policies missing on FortiGate: {sorted(missing)}")
    if extra:
        errors.append(
            f"NETW-02: unexpected policies on FortiGate (manual edits?): {sorted(extra)}"
        )
    exp_by_name = {p["name"]: p for p in exp_policies}
    act_by_name = {p["name"]: p for p in act_policies}
    for name in exp_policy_names & act_policy_names:
        for k in ("action", "src_addr", "dst_addr"):
            if exp_by_name[name].get(k) != act_by_name[name].get(k):
                errors.append(
                    f"NETW-02: policy {name} {k} drift: "
                    f"expected {exp_by_name[name].get(k)!r}, actual {act_by_name[name].get(k)!r}"
                )
    # Default-deny-all must be the last expected rule (assert at config-load time, not diff)
    if exp_policies and exp_policies[-1].get("action") != "deny":
        errors.append("NETW-02: expected last rule is not default-deny-all (config bug)")
    if act_policies and act_policies[-1].get("action") != "deny":
        errors.append("NETW-02: live FortiGate last rule is not default-deny-all")
    return errors


def _fetch_live_config() -> dict:
    # Lazy import: live mode is the only path that needs azure SDKs / requests.
    import requests  # type: ignore
    from azure.identity import DefaultAzureCredential  # type: ignore
    from azure.keyvault.secrets import SecretClient  # type: ignore

    kv_name = os.environ["KEY_VAULT_NAME"]
    cred = DefaultAzureCredential()
    secrets = SecretClient(vault_url=f"https://{kv_name}.vault.azure.net", credential=cred)
    api_token = secrets.get_secret("fortigate-api-token").value
    fgt_host = os.environ["FORTIGATE_MGMT_HOST"]
    headers = {"Authorization": f"Bearer {api_token}"}
    policies = requests.get(
        f"https://{fgt_host}/api/v2/cmdb/firewall/policy",
        headers=headers, verify=True, timeout=30,
    ).json()
    addrs = requests.get(
        f"https://{fgt_host}/api/v2/cmdb/firewall/address",
        headers=headers, verify=True, timeout=30,
    ).json()
    return {
        "policies": [
            {
                "name": p["name"],
                "action": p.get("action"),
                "src_addr": [a["name"] for a in p.get("srcaddr", [])],
                "dst_addr": [a["name"] for a in p.get("dstaddr", [])],
            }
            for p in policies.get("results", [])
        ],
        "fqdn_objects": [
            {"name": a["name"], "fqdn": a.get("fqdn")}
            for a in addrs.get("results", [])
            if a.get("type") == "fqdn"
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--drifted", action="store_true")
    args = ap.parse_args()

    expected = json.loads(POLICIES_PATH.read_text())
    if args.self_test:
        fixture = Path(
            "tests/fixtures/fortigate_drifted.json"
            if args.drifted
            else "tests/fixtures/fortigate_clean.json"
        )
        actual = json.loads(fixture.read_text())
    else:
        actual = _fetch_live_config()

    errors = _diff(expected, _normalize(actual))

    if args.drifted:
        if not errors:
            print(
                "NETW-02 self-test FAIL: drifted fixture produced no errors",
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            f"NETW-02 self-test PASS (gate correctly fired on drift: {len(errors)} differences)"
        )
        sys.exit(0)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    print(
        f"NETW-02 OK: live FortiGate matches policies.json "
        f"({len(expected.get('policies', []))} policies)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
