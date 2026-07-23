#!/usr/bin/env python3
"""Generate comprehensive conformance vectors for the Actenon protocol.

This script generates the full set of test vectors that an external
implementation must pass to claim "Actenon-compatible v1.1.0".

Vectors are written as individual JSON files under conformance/vectors/
so they can be consumed by any language's test runner.

Run: python conformance/generate_vectors.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

VECTORS_DIR = Path(__file__).resolve().parent / "vectors"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_PROOF_KEY = {
    "algorithm": "EdDSA",
    "public_key": "11qYCYQ4eBJ7eQkLZqW8FQqK4vBd8c6Y4vBd8c6Y4vB",
    "key_id": "ed25519-a1b2c3d4e5f6",
}

ACTION_HASH = {
    "algorithm": "sha256",
    "value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}

SIGNATURE_PLACEHOLDER = {
    "algorithm": "EdDSA",
    "key_id": "ed25519-a1b2c3d4e5f6",
    "value": "A" * 88,
}


def write_vector(category: str, sub: str, name: str, vector: dict) -> None:
    """Write a vector to conformance/vectors/<category>/<sub>/<name>.v1.json."""
    d = VECTORS_DIR / category / sub
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}.v1.json"
    with path.open("w") as f:
        json.dump(vector, f, indent=2, ensure_ascii=False)
        f.write("\n")


def base_proof(**overrides) -> dict:
    """A minimal valid brokered proof. Overrides replace top-level fields.
    Keys starting with _ are vector metadata, not artefact fields."""
    artefact = {
        "protocol_version": "1.0.0",
        "proof_id": "proof_a1b2c3d4e5f6071829384756abcdef01",
        "issuer": {
            "issuer_id": "actenon-permit-local",
            "issuer_type": "authority_broker",
            "key_discovery": {
                "method": "embedded",
                "embedded_key": VALID_PROOF_KEY,
            },
            "trust_status": "active",
        },
        "subject": "agent:refund-bot-001",
        "audience": {"type": "service", "id": "actenon-cloud-gateway"},
        "action": {
            "type": "payment.refund",
            "parameters": {
                "invoice_id": "inv_abc123",
                "amount_cents": 2500,
                "currency": "GBP",
            },
        },
        "target": {"type": "payment-provider", "id": "stripe"},
        "issued_at": "2026-07-21T12:00:00Z",
        "expires_at": "2026-07-21T12:15:00Z",
        "canonicalisation": "ACTENON-JCS-STRICT-1",
        "action_hash": ACTION_HASH,
        "signature": SIGNATURE_PLACEHOLDER,
        "execution_mode": "brokered",
        "grant_id": "grant_9f3c1a175e9b4d80a1b2c3d4e5f60718",
        "authority_decision_id": "authz_1234567890abcdef1234567890abcdef",
    }
    # Extract vector metadata (keys starting with _)
    name = overrides.pop("_name", "generated")
    desc = overrides.pop("_desc", "")
    expected = overrides.pop("_expected", "valid")
    # Apply artefact overrides
    for k, v in overrides.items():
        if v is None:
            artefact.pop(k, None)
        else:
            artefact[k] = v
    return {
        "name": name,
        "description": desc,
        "artefact": artefact,
        "expected_validation": expected,
    }


def base_receipt(**overrides) -> dict:
    """A minimal valid brokered succeeded receipt."""
    artefact = {
        "protocol_version": "1.0.0",
        "receipt_id": "rcpt_abcdef0123456789abcdef0123456789",
        "proof_id": "proof_a1b2c3d4e5f6071829384756abcdef01",
        "execution_attempt_id": "exec_abcdef0123456789abcdef0123456789",
        "execution_mode": "brokered",
        "executed_at": "2026-07-21T12:00:05Z",
        "outcome": "EXECUTED",
        "target": {"type": "payment-provider", "id": "stripe"},
        "action": {
            "type": "payment.refund",
            "parameters": {"invoice_id": "inv_abc123", "amount_cents": 2500},
        },
        "provider_response_summary": {
            "status": "succeeded",
            "provider_ref": "re_abc123",
        },
    }
    name = overrides.pop("_name", "generated")
    desc = overrides.pop("_desc", "")
    expected = overrides.pop("_expected", "valid")
    for k, v in overrides.items():
        if v is None:
            artefact.pop(k, None)
        else:
            artefact[k] = v
    return {
        "name": name,
        "description": desc,
        "artefact": artefact,
        "expected_validation": expected,
    }


def base_refusal(**overrides) -> dict:
    """A minimal valid refusal."""
    artefact = {
        "protocol_version": "1.0.0",
        "refusal_id": "rful_abcdef0123456789abcdef0123456789",
        "proof_id": "proof_a1b2c3d4e5f6071829384756abcdef01",
        "execution_attempt_id": "exec_abcdef0123456789abcdef0123456789",
        "execution_mode": "brokered",
        "refused_at": "2026-07-21T12:00:03Z",
        "disclosed_code": "PROOF_INVALID",
        "internal_code": "SIGNATURE_INVALID",
        "retryable": False,
        "message": "Signature verification failed.",
    }
    name = overrides.pop("_name", "generated")
    desc = overrides.pop("_desc", "")
    expected = overrides.pop("_expected", "valid")
    for k, v in overrides.items():
        if v is None:
            artefact.pop(k, None)
        else:
            artefact[k] = v
    return {
        "name": name,
        "description": desc,
        "artefact": artefact,
        "expected_validation": expected,
    }


# ---------------------------------------------------------------------------
# Proof vectors
# ---------------------------------------------------------------------------

def generate_proof_vectors():
    """Generate comprehensive proof vectors."""
    # --- Valid proofs ---
    valid_proofs = [
        ("minimal_brokered", "Minimal valid brokered proof.", {}),
        ("minimal_resource_owned", "Minimal valid resource_owned proof.", {
            "execution_mode": "resource_owned",
            "issuer": {
                "issuer_id": "resource:payments-api",
                "issuer_type": "resource_owner",
                "key_discovery": {"method": "embedded", "embedded_key": VALID_PROOF_KEY},
                "trust_status": "active",
            },
        }),
        ("action_data_destruction", "Proof for a data-destruction action.", {
            "action": {"type": "data.delete", "parameters": {"table": "audit_log", "scope": "all"}},
            "target": {"type": "database", "id": "prod_primary"},
        }),
        ("action_deployment", "Proof for a deployment action.", {
            "action": {"type": "deploy.apply", "parameters": {"manifest": "k8s/prod.yaml", "namespace": "prod"}},
            "target": {"type": "kubernetes-cluster", "id": "prod-cluster"},
        }),
        ("action_access_control", "Proof for an IAM access-control change.", {
            "action": {"type": "iam.put_user_policy", "parameters": {"user": "agent-bot", "policy": "arn:aws:iam::123:policy/PowerUserAccess"}},
            "target": {"type": "aws-iam", "id": "aws-account-123"},
        }),
        ("action_data_export", "Proof for a sensitive data export.", {
            "action": {"type": "data.export", "parameters": {"dataset": "customer_pii", "format": "csv", "destination": "s3://exports/"}},
            "target": {"type": "data-warehouse", "id": "snowflake-prod"},
        }),
        ("action_communication", "Proof for a communication action.", {
            "action": {"type": "email.send", "parameters": {"to": "customer@example.com", "template": "refund-notice"}},
            "target": {"type": "email-provider", "id": "ses"},
        }),
        ("with_well_known_key_discovery", "Proof using well-known URL key discovery.", {
            "issuer": {
                "issuer_id": "actenon-cloud",
                "issuer_type": "authority_broker",
                "key_discovery": {"method": "well_known", "well_known_url": "https://actenon.cloud/.well-known/actenon/keys.json"},
                "trust_status": "active",
            },
        }),
        ("with_evidence_links", "Proof with transparency log + counter-signature evidence.", {
            "evidence_links": [
                {"type": "transparency_log", "link_type": "external_url", "target_ref": {"url": "https://log.actenon.dev/v1/entries/123"}},
                {"type": "counter_signature", "link_type": "inline", "target_ref": {"inline_payload": {"signer": "actenon-cloud", "key_id": "cs-key-1", "signature": "B" * 88}}},
            ],
        }),
        ("with_approval_artefact", "Proof with a custom_claims field carrying approval metadata.", {
            "custom_claims": {
                "approval_id": "appr_abcdef0123456789",
                "approved_by": "human:finance-lead",
                "approved_at": "2026-07-21T11:59:00Z",
                "approval_scope": "payment.refund > 20 USD",
            },
        }),
        ("long_expiry_window", "Proof with a 1-hour validity window.", {
            "issued_at": "2026-07-21T12:00:00Z",
            "expires_at": "2026-07-21T13:00:00Z",
        }),
        ("short_expiry_window", "Proof with a 30-second validity window.", {
            "issued_at": "2026-07-21T12:00:00Z",
            "expires_at": "2026-07-21T12:00:30Z",
        }),
        ("empty_parameters", "Proof for an action with no parameters.", {
            "action": {"type": "system.healthcheck", "parameters": {}},
        }),
        ("nested_parameters", "Proof with deeply nested action parameters.", {
            "action": {
                "type": "infra.provision",
                "parameters": {
                    "cluster": {"name": "prod", "region": "us-east-1", "nodes": 3},
                    "networking": {"vpc": "vpc-abc", "subnets": ["subnet-1", "subnet-2"]},
                },
            },
        }),
        ("unicode_parameters", "Proof with Unicode in action parameters.", {
            "action": {
                "type": "issue.create",
                "parameters": {"title": "修复支付问题", "body": "用户报告退款失败 — 请检查"},
            },
        }),
    ]

    for name, desc, overrides in valid_proofs:
        vector = base_proof(_name=name, _desc=desc, _expected="valid", **overrides)
        write_vector("proof", "valid", name, vector)

    # --- Invalid proofs ---
    # Note: vectors that test RUNTIME constraints (time windows, float
    # rejection, issuer revocation) are not included here because the
    # schema-validation test only checks JSON Schema + Pydantic + identifier
    # validation. Runtime constraints are tested by the Kernel's verifier
    # suite, not the protocol schema suite.
    invalid_proofs = [
        ("missing_proof_id", "Proof missing the required proof_id field.", {
            "proof_id": None,
        }, "MISSING_REQUIRED_FIELD"),
        ("invalid_proof_id_prefix", "Proof with a forbidden proof_id prefix (tenant_).", {
            "proof_id": "tenant_abcdef0123456789",
        }, "INVALID_IDENTIFIER"),
        ("unsupported_protocol_version", "Proof with a future major version (2.0.0).", {
            "protocol_version": "2.0.0",
        }, "UNSUPPORTED_PROTOCOL_VERSION"),
        ("invalid_execution_mode", "Proof with an invalid execution_mode value.", {
            "execution_mode": "hybrid",
        }, "SCHEMA_INVALID"),
        ("unsupported_canonicalisation", "Proof with an unsupported canonicalisation profile.", {
            "canonicalisation": "JSON-LD-1.1",
        }, "UNSUPPORTED_CANONICALISATION"),
        ("missing_signature", "Proof missing the signature object entirely.", {
            "signature": None,
        }, "MISSING_REQUIRED_FIELD"),
        ("missing_action_hash", "Proof missing the action_hash.", {
            "action_hash": None,
        }, "MISSING_REQUIRED_FIELD"),
        ("missing_issuer", "Proof missing the issuer object.", {
            "issuer": None,
        }, "MISSING_REQUIRED_FIELD"),
        ("issuer_no_key_discovery", "Proof whose issuer has no key_discovery method.", {
            "issuer": {
                "issuer_id": "actenon-permit-local",
                "issuer_type": "authority_broker",
                "trust_status": "active",
            },
        }, "MISSING_REQUIRED_FIELD"),
        ("missing_action_type", "Proof whose action has no type field.", {
            "action": {"parameters": {"foo": "bar"}},
        }, "SCHEMA_INVALID"),
        ("missing_execution_mode", "Proof with no execution_mode field.", {
            "execution_mode": None,
        }, "MISSING_REQUIRED_FIELD"),
        ("approval_prefix_proof_id", "Proof with an approval_ prefix on proof_id (forbidden).", {
            "proof_id": "approval_abcdef0123456789",
        }, "INVALID_IDENTIFIER"),
        ("user_prefix_proof_id", "Proof with a user_ prefix on proof_id (forbidden).", {
            "proof_id": "user_abcdef0123456789",
        }, "INVALID_IDENTIFIER"),
        ("policy_prefix_proof_id", "Proof with a policy_ prefix on proof_id (forbidden).", {
            "proof_id": "policy_abcdef0123456789",
        }, "INVALID_IDENTIFIER"),
    ]

    for name, desc, overrides, expected_code in invalid_proofs:
        vector = base_proof(_name=name, _desc=desc, _expected="invalid", **overrides)
        vector["expected_refusal_code"] = expected_code
        write_vector("proof", "invalid", name, vector)


# ---------------------------------------------------------------------------
# Receipt vectors
# ---------------------------------------------------------------------------

def generate_receipt_vectors():
    """Generate comprehensive receipt vectors."""
    valid_receipts = [
        ("executed_brokered", "Successful brokered execution.", {
            "execution_mode": "brokered",
            "outcome": "EXECUTED",
            "provider_response_summary": {"status": "succeeded", "provider_ref": "re_abc123"},
        }),
        ("executed_resource_owned", "Successful resource-owned execution.", {
            "execution_mode": "resource_owned",
            "outcome": "EXECUTED",
            "resource_signature": {"algorithm": "EdDSA", "key_id": "res-key-1", "value": "C" * 88},
        }),
        ("failed_brokered", "Brokered execution where the provider returned an error (outcome is still EXECUTED — the action ran).", {
            "execution_mode": "brokered",
            "outcome": "EXECUTED",
            "provider_response_summary": {"status": "error", "error_code": "card_declined"},
        }),
        ("outcome_unknown_brokered", "Brokered execution where provider response was not observed.", {
            "execution_mode": "brokered",
            "outcome": "UNKNOWN",
            "provider_response_summary": None,
        }),
        ("refused_receipt_brokered", "Receipt for an execution that was refused before side effect.", {
            "execution_mode": "brokered",
            "outcome": "REFUSED",
            "refusal_id": "rful_abcdef0123456789",
        }),
        ("partial_brokered", "Brokered execution with partial success.", {
            "execution_mode": "brokered",
            "outcome": "PARTIAL",
            "provider_response_summary": {"status": "partial", "completed": 3, "total": 5},
        }),
        ("refused_resource_owned", "Resource-owned execution refused at the boundary.", {
            "execution_mode": "resource_owned",
            "outcome": "REFUSED",
            "refusal_id": "rful_abcdef0123456789",
        }),
        ("executed_with_long_action_parameters", "Receipt with large nested action parameters.", {
            "action": {
                "type": "infra.provision",
                "parameters": {
                    "cluster": {"name": "prod", "region": "us-east-1", "nodes": 3},
                    "networking": {"vpc": "vpc-abc", "subnets": ["subnet-1", "subnet-2", "subnet-3"]},
                },
            },
        }),
        ("with_evidence_links", "Receipt with a transparency log evidence link.", {
            "evidence_links": [
                {"type": "transparency_log", "link_type": "external_url", "target_ref": {"url": "https://log.actenon.dev/v1/entries/456"}},
            ],
        }),
        ("with_additional_evidence", "Receipt with an external attestation evidence link.", {
            "evidence_links": [
                {"type": "external_attestation", "link_type": "external_url", "target_ref": {"url": "https://attest.actenon.dev/v1/receipts/rcpt_abc"}},
            ],
        }),
        ("minimal_fields", "Receipt with only the required fields.", {}),
        ("unicode_action_parameters", "Receipt with Unicode in action parameters.", {
            "action": {
                "type": "issue.create",
                "parameters": {"title": "修复支付问题", "body": "用户报告退款失败"},
            },
        }),
    ]

    for name, desc, overrides in valid_receipts:
        vector = base_receipt(_name=name, _desc=desc, _expected="valid", **overrides)
        write_vector("receipt", "valid", name, vector)

    invalid_receipts = [
        ("missing_receipt_id", "Receipt missing receipt_id.", {"receipt_id": None}, "MISSING_REQUIRED_FIELD"),
        ("invalid_outcome", "Receipt with an invalid outcome value.", {"outcome": "PENDING"}, "SCHEMA_INVALID"),
        ("missing_execution_mode", "Receipt with no execution_mode field.", {"execution_mode": None}, "MISSING_REQUIRED_FIELD"),
        ("missing_proof_id", "Receipt missing proof_id.", {"proof_id": None}, "MISSING_REQUIRED_FIELD"),
        ("missing_executed_at", "Receipt missing executed_at.", {"executed_at": None}, "MISSING_REQUIRED_FIELD"),
        ("missing_outcome", "Receipt missing outcome.", {"outcome": None}, "MISSING_REQUIRED_FIELD"),
        ("missing_target", "Receipt missing target.", {"target": None}, "MISSING_REQUIRED_FIELD"),
        ("missing_action", "Receipt missing action.", {"action": None}, "MISSING_REQUIRED_FIELD"),
    ]

    for name, desc, overrides, expected_code in invalid_receipts:
        vector = base_receipt(_name=name, _desc=desc, _expected="invalid", **overrides)
        vector["expected_refusal_code"] = expected_code
        write_vector("receipt", "invalid", name, vector)


# ---------------------------------------------------------------------------
# Refusal vectors — cover all 20 codes
# ---------------------------------------------------------------------------

def generate_refusal_vectors():
    """Generate refusal vectors covering all 20 codes from the catalogue."""
    # All 20 codes from refusals/catalogue.v1.yaml
    # (code, disclosed_code, internal_code, retryable, description)
    refusal_codes = [
        # Request-shape refusals
        ("malformed_request", "MALFORMED_REQUEST", "MALFORMED_REQUEST", False, "Request could not be parsed."),
        ("unsupported_protocol_version", "UNSUPPORTED_PROTOCOL_VERSION", "UNSUPPORTED_PROTOCOL_VERSION", False, "Protocol version major not supported."),
        ("canonicalisation_failure", "CANONICALISATION_FAILURE", "CANONICALISATION_FAILURE", False, "Canonicalisation profile not recognised or failed."),
        # Proof-presence refusals
        ("proof_missing", "PROOF_MISSING", "PROOF_MISSING", False, "No proof supplied for a protected action."),
        # Proof-validity refusals (umbrella + detailed)
        ("proof_invalid_umbrella", "PROOF_INVALID", None, False, "Umbrella proof-invalid code (no specific internal code)."),
        ("issuer_untrusted", "PROOF_INVALID", "ISSUER_UNTRUSTED", False, "Issuer is not in the verifier's trust store."),
        ("signature_invalid", "PROOF_INVALID", "SIGNATURE_INVALID", False, "Signature verification failed."),
        ("proof_expired", "PROOF_EXPIRED", "PROOF_EXPIRED", False, "Proof expired before execution attempt."),
        ("proof_not_yet_valid", "PROOF_NOT_YET_VALID", "PROOF_NOT_YET_VALID", True, "Proof not yet valid (issued_at in the future)."),
        ("audience_mismatch", "PROOF_INVALID", "AUDIENCE_MISMATCH", False, "Proof audience does not match this endpoint."),
        ("target_mismatch", "PROOF_INVALID", "TARGET_MISMATCH", False, "Proof target does not match the attempted target."),
        ("action_mismatch", "PROOF_INVALID", "ACTION_MISMATCH", False, "Proof action type does not match the attempted action."),
        ("parameter_mismatch", "PROOF_INVALID", "PARAMETER_MISMATCH", False, "Action parameters do not match the proof."),
        # Replay + authority refusals
        ("replay_detected", "REPLAY_DETECTED", "REPLAY_DETECTED", False, "Proof already consumed (single-use violation)."),
        ("authority_revoked", "AUTHORITY_REVOKED", "AUTHORITY_REVOKED", False, "Grant or capability has been revoked."),
        # Policy + execution refusals
        ("policy_refusal", "POLICY_REFUSAL", "POLICY_REFUSAL", False, "Policy engine returned DENY."),
        ("credential_unavailable", "CREDENTIAL_UNAVAILABLE", "CREDENTIAL_UNAVAILABLE", True, "Credential broker could not resolve the credential — retryable."),
        ("provider_refusal", "PROVIDER_REFUSAL", "PROVIDER_REFUSAL", False, "Provider refused the action."),
        ("provider_failure", "PROVIDER_FAILURE", "PROVIDER_FAILURE", True, "Provider returned a transient failure — retryable."),
        ("outcome_unknown", "OUTCOME_UNKNOWN", "OUTCOME_UNKNOWN", True, "Execution outcome could not be determined."),
    ]

    for name, disclosed, internal, retryable, desc in refusal_codes:
        overrides = {
            "disclosed_code": disclosed,
            "retryable": retryable,
            "message": desc,
        }
        if internal:
            overrides["internal_code"] = internal
        else:
            overrides["internal_code"] = None

        vector = base_refusal(
            _name=name,
            _desc=desc,
            _expected="valid",
            **overrides,
        )
        write_vector("refusal", "valid", name, vector)

    # Invalid refusals
    invalid_refusals = [
        ("unknown_disclosed_code", "Refusal with a code not in the catalogue.", {
            "disclosed_code": "UNKNOWN_CODE",
        }, "UNKNOWN_REFUSAL_CODE"),
        ("internal_without_disclosed_match", "Internal code that doesn't map to its disclosed umbrella.", {
            "disclosed_code": "PROOF_INVALID",
            "internal_code": "REPLAY_DETECTED",  # REPLAY_DETECTED is its own disclosed code, not under PROOF_INVALID
        }, "DISCLOSURE_POLICY_VIOLATION"),
        ("retryable_mismatch", "Retryable flag contradicts the code's catalogue entry.", {
            "disclosed_code": "PROOF_INVALID",
            "internal_code": "SIGNATURE_INVALID",
            "retryable": True,  # SIGNATURE_INVALID is not retryable
        }, "RETRYABILITY_MISMATCH"),
        ("missing_disclosed_code", "Refusal with no disclosed_code.", {
            "disclosed_code": None,
        }, "MISSING_REQUIRED_FIELD"),
        ("missing_refusal_id", "Refusal missing refusal_id.", {
            "refusal_id": None,
        }, "MISSING_REQUIRED_FIELD"),
    ]

    for name, desc, overrides, expected_code in invalid_refusals:
        vector = base_refusal(_name=name, _desc=desc, _expected="invalid", **overrides)
        vector["expected_refusal_code"] = expected_code
        write_vector("refusal", "invalid", name, vector)


# ---------------------------------------------------------------------------
# Execution-mode vectors
# ---------------------------------------------------------------------------

def generate_execution_mode_vectors():
    """Generate execution-mode distinction vectors."""
    vectors = [
        ("brokered_mode_explicit", "Brokered mode is explicitly set on the proof.", {
            "input": {"execution_mode": "brokered"},
            "expected_mode": "brokered",
        }),
        ("resource_owned_mode_explicit", "Resource-owned mode is explicitly set on the proof.", {
            "input": {"execution_mode": "resource_owned"},
            "expected_mode": "resource_owned",
        }),
        ("mode_must_be_explicit", "Mode must not be inferred — missing mode is invalid.", {
            "input": {},
            "expected_validation": "invalid",
            "expected_error": "MISSING_EXECUTION_MODE",
        }),
        ("mode_must_be_string", "Mode must be a string, not a number.", {
            "input": {"execution_mode": 1},
            "expected_validation": "invalid",
            "expected_error": "SCHEMA_INVALID",
        }),
        ("brokered_result_has_brokered_fields", "Brokered result must have brokered-only fields.", {
            "input": {"mode": "brokered", "result": {"provider_response_summary": {"status": "succeeded"}}},
            "expected_validation": "valid",
        }),
        ("resource_owned_result_has_resource_fields", "Resource-owned result must have resource-only fields.", {
            "input": {"mode": "resource_owned", "result": {"resource_signature": {"algorithm": "EdDSA", "value": "x"}}},
            "expected_validation": "valid",
        }),
        ("brokered_result_missing_provider_response", "Brokered succeeded result without provider_response_summary is invalid.", {
            "input": {"mode": "brokered", "result": {"outcome": "EXECUTED"}},
            "expected_validation": "invalid",
            "expected_error": "BROKERED_SUCCEEDED_REQUIRES_OBSERVATION",
        }),
        ("resource_owned_result_missing_resource_signature", "Resource-owned succeeded result without resource_signature is invalid.", {
            "input": {"mode": "resource_owned", "result": {"outcome": "SUCCEEDED"}},
            "expected_validation": "invalid",
            "expected_error": "RESOURCE_OWNED_SUCCEEDED_REQUIRES_SIGNATURE",
        }),
        ("submitted_is_non_final", "submitted state must be non-final.", {
            "input": {"mode": "resource_owned", "result": {"outcome": "SUBMITTED"}},
            "expected_finality": "non_final",
        }),
        ("succeeded_is_final", "succeeded state must be final.", {
            "input": {"mode": "resource_owned", "result": {"outcome": "SUCCEEDED", "resource_signature": {"algorithm": "EdDSA", "value": "x"}}},
            "expected_finality": "final",
        }),
    ]

    d = VECTORS_DIR / "execution-mode" / "valid"
    d.mkdir(parents=True, exist_ok=True)
    for name, desc, body in vectors:
        vector = {"name": name, "description": desc, **body}
        path = d / f"{name}.v1.json"
        with path.open("w") as f:
            json.dump(vector, f, indent=2, ensure_ascii=False)
            f.write("\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Actenon protocol conformance vectors...")
    print(f"  Output: {VECTORS_DIR}")
    print()

    generate_proof_vectors()
    valid_p = len(list((VECTORS_DIR / "proof" / "valid").glob("*.json")))
    invalid_p = len(list((VECTORS_DIR / "proof" / "invalid").glob("*.json")))
    print(f"  proof:        {valid_p:3d} valid, {invalid_p:3d} invalid")

    generate_receipt_vectors()
    valid_r = len(list((VECTORS_DIR / "receipt" / "valid").glob("*.json")))
    invalid_r = len(list((VECTORS_DIR / "receipt" / "invalid").glob("*.json")))
    print(f"  receipt:      {valid_r:3d} valid, {invalid_r:3d} invalid")

    generate_refusal_vectors()
    valid_rf = len(list((VECTORS_DIR / "refusal" / "valid").glob("*.json")))
    invalid_rf = len(list((VECTORS_DIR / "refusal" / "invalid").glob("*.json")))
    print(f"  refusal:      {valid_rf:3d} valid, {invalid_rf:3d} invalid")

    generate_execution_mode_vectors()
    valid_em = len(list((VECTORS_DIR / "execution-mode" / "valid").glob("*.json")))
    print(f"  exec-mode:    {valid_em:3d} valid")

    # Count canonicalisation (already existing, not regenerated)
    valid_c = len(list((VECTORS_DIR / "canonicalisation" / "valid").glob("*.json")))
    invalid_c = len(list((VECTORS_DIR / "canonicalisation" / "invalid").glob("*.json")))
    print(f"  canonical:    {valid_c:3d} valid, {invalid_c:3d} invalid  (existing, untouched)")

    # Count execution-result (already existing)
    valid_er = len(list((VECTORS_DIR / "execution-result" / "valid").glob("*.json")))
    invalid_er = len(list((VECTORS_DIR / "execution-result" / "invalid").glob("*.json")))
    print(f"  exec-result:  {valid_er:3d} valid, {invalid_er:3d} invalid  (existing, untouched)")

    total = (valid_p + invalid_p + valid_r + invalid_r + valid_rf + invalid_rf +
             valid_em + valid_c + invalid_c + valid_er + invalid_er)
    print()
    print(f"  TOTAL: {total} vectors")


if __name__ == "__main__":
    main()
