"""Capability provenance: exact Scan-named powers, no widen, no forged token.

Kernel PR #43 refuses a capability outside the edge allow-list with
SCOPE_CAPABILITY_MISMATCH, and refuses a token that was never signed.
Permit PR #23 mints one concrete capability and signs extensions.authority.
These tests are the protocol rules those callers share.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from actenon_protocol import (
    CapabilityError,
    DisclosurePolicy,
    authority_extension,
    capability_in_scope,
    parse_authority_extension,
    refusal_to_disclosed_code,
    refusal_to_internal_code,
    scope_capabilities_for_mint,
    scope_capabilities_for_verification,
    unauthenticated_refusal,
)
from actenon_protocol.types import ExecutionProof, ExecutionRefusal
from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def _registry() -> Registry:
    schemas = {}
    for path in SCHEMAS.glob("*.v1.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schemas[schema["$id"]] = schema

    def retrieve(uri: str):
        return Resource.from_contents(schemas[uri])

    return Registry(retrieve=retrieve)


def test_edge_capability_mismatch_stays_its_own_code():
    """Trusted disclosure must not rewrite the edge failure as a parameter mismatch."""
    code = "SCOPE_CAPABILITY_MISMATCH"
    assert refusal_to_disclosed_code(code, DisclosurePolicy.PUBLIC) == "PROOF_INVALID"
    assert refusal_to_internal_code(code, DisclosurePolicy.PUBLIC) is None
    assert refusal_to_internal_code(code, DisclosurePolicy.TRUSTED) == code
    assert (
        refusal_to_internal_code("SCOPE_MODE_INVALID", DisclosurePolicy.TRUSTED)
        == "SCOPE_MODE_INVALID"
    )


def test_mint_refuses_to_widen_an_empty_or_wildcard_scope():
    with pytest.raises(CapabilityError, match="empty allow-list"):
        scope_capabilities_for_mint(())
    with pytest.raises(CapabilityError, match="wildcard"):
        scope_capabilities_for_mint(("payment.*",))
    with pytest.raises(CapabilityError, match="wildcard"):
        scope_capabilities_for_mint(("*",))
    assert scope_capabilities_for_mint(("payment.refund",)) == ("payment.refund",)
    assert scope_capabilities_for_mint(("filesystem.write", "airlock.http.post")) == (
        "filesystem.write",
        "airlock.http.post",
    )


def test_verification_empty_allow_list_does_not_become_the_attempted_action():
    assert scope_capabilities_for_verification(None, "payment.refund") == ("payment.refund",)
    assert scope_capabilities_for_verification((), "payment.refund") == ()
    assert capability_in_scope("payment.refund", ()) is False
    assert capability_in_scope("payment.refund", ("filesystem.write",)) is False
    assert capability_in_scope("filesystem.write", ("filesystem.write",)) is True
    assert capability_in_scope("payment.*", ("payment.*",)) is False
    with pytest.raises(CapabilityError, match="wildcard"):
        scope_capabilities_for_verification(("*",), "payment.refund")


def test_token_length_is_not_acceptance():
    token = "A" * 32
    assert len(token) >= 16
    assert (
        unauthenticated_refusal(trust_root_configured=False, signature_verified=False)
        == "ISSUER_UNTRUSTED"
    )
    assert (
        unauthenticated_refusal(trust_root_configured=True, signature_verified=False)
        == "SIGNATURE_INVALID"
    )
    assert unauthenticated_refusal(trust_root_configured=True, signature_verified=True) is None


def test_authority_extension_round_trip():
    extensions = authority_extension(
        issuer="service:actenon-permit",
        grant_id="grant_9f3c1a175e9b4d80a1b2c3d4e5f60718",
    )
    assert extensions == {
        "authority": {
            "issuer": "service:actenon-permit",
            "grant_id": "grant_9f3c1a175e9b4d80a1b2c3d4e5f60718",
            "revocable": True,
        }
    }
    parsed = parse_authority_extension(extensions)
    assert parsed["revocable"] is True
    with pytest.raises(CapabilityError, match="no authority"):
        parse_authority_extension({})


def test_proof_schema_accepts_signed_authority_extension():
    vector = json.loads(
        (ROOT / "conformance/vectors/proof/valid/minimal_brokered.v1.json").read_text(
            encoding="utf-8"
        )
    )
    artefact = vector["artefact"]
    artefact["extensions"] = authority_extension(
        issuer="service:actenon-permit",
        grant_id=artefact["grant_id"],
    )
    schema = json.loads((SCHEMAS / "execution_proof.v1.json").read_text(encoding="utf-8"))
    validator_for(schema).check_schema(schema)
    errors = list(Draft202012Validator(schema, registry=_registry()).iter_errors(artefact))
    assert errors == []
    proof = ExecutionProof(**artefact)
    assert proof.extensions is not None
    assert proof.extensions.authority is not None
    assert proof.extensions.authority.revocable is True


def test_refusal_schema_accepts_capability_mismatch_internally():
    artefact = {
        "protocol_version": "1.2.0",
        "refusal_id": "rful_abcdef0123456789abcdef0123456789",
        "execution_mode": "brokered",
        "refused_at": "2026-10-04T00:00:00Z",
        "disclosed_code": "PROOF_INVALID",
        "internal_code": "SCOPE_CAPABILITY_MISMATCH",
        "retryable": False,
    }
    schema = json.loads((SCHEMAS / "execution_refusal.v1.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, registry=_registry()).iter_errors(artefact))
    assert errors == []
    refusal = ExecutionRefusal.from_internal_code(
        refusal_id=artefact["refusal_id"],
        internal_code="SCOPE_CAPABILITY_MISMATCH",
        execution_mode="brokered",
        refused_at=artefact["refused_at"],
        policy=DisclosurePolicy.TRUSTED,
    )
    assert refusal.internal_code == "SCOPE_CAPABILITY_MISMATCH"
    assert refusal.disclosed_code == "PROOF_INVALID"
