"""Common type definitions shared across all protocol artefacts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from actenon_protocol.version import PROTOCOL_VERSION

# Type aliases (validated via Annotated constraints)

ProtocolVersion = Annotated[
    str,
    StringConstraints(pattern=r"^1\.[0-9]+\.[0-9]+$"),
    Field(description=f"Protocol version. Current: {PROTOCOL_VERSION}"),
]

Identifier = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]*_[0-9a-f]{16,}$"),
    Field(description="Actenon protocol identifier: <prefix><hex_chars>"),
]

Iso8601Timestamp = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})$"),
    Field(description="ISO 8601 timestamp with timezone. UTC recommended."),
]

EvidenceLinkType = Literal[
    "transparency_log",
    "receipt_chain",
    "audit_ledger",
    "external_attestation",
    "counter_signature",
]


class AudienceRef(BaseModel):
    """The intended audience (verifier service) for a proof."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(description="Audience type. Examples: 'service', 'resource', 'tenant'.")
    id: str = Field(description="Audience identifier. Examples: 'actenon-cloud-gateway'.")


class TargetRef(BaseModel):
    """The target resource of an action."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(description="Target type. Examples: 'payment-provider', 'database'.")
    id: str = Field(description="Target identifier. Examples: 'stripe', 'postgres-primary'.")


class ActionSpec(BaseModel):
    """The exact action spec (type + parameters)."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(description="Action type. Examples: 'payment.refund', 'file.delete'.")
    parameters: dict = Field(
        description="Action parameters. MUST be JSON-serialisable under ACTENON-JCS-STRICT-1 (no floats)."
    )


class ActionHash(BaseModel):
    """The hash of the canonicalised (action, target, parameters) tuple."""

    model_config = ConfigDict(extra="forbid")

    algorithm: str = Field(default="sha256", description="Hash algorithm. Default: 'sha256'.")
    value: Annotated[
        str,
        StringConstraints(pattern=r"^[0-9a-f]{64}$"),
        Field(description="Hex-encoded SHA-256 hash (lowercase)."),
    ]


class Signature(BaseModel):
    """A cryptographic signature over canonicalised payload."""

    model_config = ConfigDict(extra="forbid")

    algorithm: str = Field(description="Signature algorithm. Examples: 'EdDSA', 'ES256'.")
    key_id: str = Field(description="Signing key identifier.")
    value: str = Field(description="Base64url-encoded signature value (no padding).")
