"""IssuerMetadata pydantic model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EmbeddedKey(BaseModel):
    model_config = ConfigDict(extra="forbid")
    algorithm: str
    public_key: str = Field(description="Base64url-encoded public key.")
    key_id: str


class KeyDiscovery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["well_known", "embedded", "external_registry"]
    well_known_url: str | None = None
    embedded_key: EmbeddedKey | None = None
    external_registry_url: str | None = None


class KeyRotationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rotation_period_days: int = Field(ge=1)
    overlap_period_days: int = Field(ge=0)


class IssuerMetadata(BaseModel):
    """Metadata about the issuer of an ExecutionProof."""

    model_config = ConfigDict(extra="forbid")

    issuer_id: str
    issuer_type: Literal["authority_broker", "resource_owner", "delegated_signer"]
    key_discovery: KeyDiscovery
    trust_status: Literal["active", "suspended", "revoked"] | None = None
    key_rotation_policy: KeyRotationPolicy | None = None
