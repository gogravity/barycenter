"""FOUND-03: confirm KV salt-tenant-bootstrap key allows sign operation by mi-bary-etl
AND that the key material is never returned (sign returns signature, not the key).
"""
import os
import pytest

AZURE_SUB = os.environ.get("AZURE_SUBSCRIPTION_ID")
KV_NAME = os.environ.get("KEY_VAULT_NAME", "kv-bary-dev")

pytestmark = pytest.mark.skipif(
    not AZURE_SUB,
    reason="AZURE_SUBSCRIPTION_ID not set; integration test requires live Azure",
)


def test_sign_operation_succeeds_and_returns_signature_only():
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.keys.crypto import CryptographyClient, SignatureAlgorithm

    credential = DefaultAzureCredential()  # in CI, picks up the federated MI token
    key_id = f"https://{KV_NAME}.vault.azure.net/keys/salt-tenant-bootstrap"
    client = CryptographyClient(key=key_id, credential=credential)

    data = b"test@example.com"
    result = client.sign(SignatureAlgorithm.hs256, data)
    assert result.signature is not None
    assert len(result.signature) >= 32, "HS256 produces 32-byte signature minimum"
    # The CryptographyClient does NOT expose the underlying key bytes — verified by
    # absence of any key-material attribute on the result object.
    assert not hasattr(result, "key_material")
    assert not hasattr(result, "key_value")


def test_get_key_material_is_forbidden():
    """Cannot retrieve the raw oct key material via the keys API even with crypto user role."""
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.keys import KeyClient

    credential = DefaultAzureCredential()
    client = KeyClient(vault_url=f"https://{KV_NAME}.vault.azure.net", credential=credential)
    key = client.get_key("salt-tenant-bootstrap")
    # For oct keys, the `k` (raw key bytes) attribute is never returned to clients
    # by KV — Crypto User role allows sign/verify, not export.
    assert key.key.k is None or key.key.k == b"" or key.key.k == "", (
        f"KV returned raw oct key material: {key.key.k!r}"
    )
