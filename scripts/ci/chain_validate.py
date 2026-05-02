"""AUDIT-01 CI gate: read all WORM audit blobs, recompute chain from genesis, fail on any mismatch.

Modes:
  --self-test: load tests/fixtures/chain_good.ndjson and validate; exit 0.
  --self-test --tampered: load tests/fixtures/chain_tampered.ndjson and validate; expect failure.
  (default): live mode — list blobs in WORM container, download, validate.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_fixture(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line.strip()]


def _list_live_entries() -> list[str]:
    # Lazy import: live mode is the only path that needs azure SDKs.
    from azure.identity import DefaultAzureCredential  # type: ignore
    from azure.storage.blob import ContainerClient  # type: ignore

    cred = DefaultAzureCredential()
    acct = os.environ["WORM_STORAGE_ACCOUNT"]
    cc = ContainerClient(
        account_url=f"https://{acct}.blob.core.windows.net",
        container_name="audit",
        credential=cred,
    )
    entries: list[str] = []
    # list_blobs returns in lexicographic name order; the WORM emit pattern names
    # blobs by deterministic timestamp + sequence so order is append order.
    for blob in cc.list_blobs():
        blob_client = cc.get_blob_client(blob.name)
        content = blob_client.download_blob().readall().decode("utf-8")
        for line in content.splitlines():
            if line.strip():
                entries.append(line)
    return entries


def main() -> None:
    from barycenter.audit.chain import validate_chain
    from barycenter.audit.exceptions import ChainIntegrityError

    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument(
        "--tampered",
        action="store_true",
        help="With --self-test, load a tampered fixture and expect failure.",
    )
    args = ap.parse_args()

    if args.self_test:
        fixture = Path(
            "tests/fixtures/chain_tampered.ndjson"
            if args.tampered
            else "tests/fixtures/chain_good.ndjson"
        )
        entries = _load_fixture(fixture)
        try:
            count = validate_chain(entries)
        except ChainIntegrityError as e:
            if args.tampered:
                print(
                    f"AUDIT-01 self-test PASS (gate correctly raised on tampered chain: {e})"
                )
                sys.exit(0)
            print(
                f"AUDIT-01 self-test FAIL: clean fixture should validate, got {e}",
                file=sys.stderr,
            )
            sys.exit(1)
        if args.tampered:
            print(
                "AUDIT-01 self-test FAIL: tampered fixture validated without raising",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"AUDIT-01 self-test PASS ({count} entries validated)")
        sys.exit(0)

    # Live mode
    entries = _list_live_entries()
    try:
        count = validate_chain(entries)
    except ChainIntegrityError as e:
        print(f"AUDIT-01 FAIL: chain integrity broken: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"AUDIT-01 OK: {count} entries validated")
    sys.exit(0)


if __name__ == "__main__":
    main()
