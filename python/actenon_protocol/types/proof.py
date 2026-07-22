"""ExecutionProof pydantic model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from actenon_protocol.execution_modes import ExecutionMode
from actenon_protocol.types.common import (
    ActionHash,
    ActionSpec,
    AudienceRef,
    Identifier,
    Iso8601Timestamp,
    ProtocolVersion,
    Signature,
    TargetRef,
)
from actenon_protocol.types.evidence import EvidenceLink
from actenon_protocol.types.issuer import IssuerMetadata


class ExecutionProof(BaseModel):
    """The cryptographic boundary artefact verified by the protected resource.

    Authorises ONE exact (action, target, parameters) tuple under the
    resource owner's configured trust policy.
    """

    model_config = ConfigDict(extra="forbid")

    protocol_version: ProtocolVersion
    proof_id: Identifier
    issuer: IssuerMetadata
    subject: str
    audience: AudienceRef
    action: ActionSpec
    target: TargetRef
    issued_at: Iso8601Timestamp
    not_before: Iso8601Timestamp | None = None
    expires_at: Iso8601Timestamp
    canonicalisation: Literal["ACTENON-JCS-STRICT-1", "RFC8785-JCS"]
    action_hash: ActionHash
    signature: Signature
    execution_mode: ExecutionMode
    grant_id: Identifier | None = None
    authority_decision_id: Identifier | None = None
    evidence_links: list[EvidenceLink] = Field(default_factory=list)
    custom_claims: dict | None = None
