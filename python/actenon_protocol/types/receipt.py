"""ExecutionReceipt pydantic model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from actenon_protocol.execution_modes import ExecutionMode
from actenon_protocol.outcome_codes import ExecutionOutcome
from actenon_protocol.types.common import (
    ActionSpec,
    Identifier,
    Iso8601Timestamp,
    ProtocolVersion,
    Signature,
    TargetRef,
)
from actenon_protocol.types.evidence import EvidenceLink


class ExecutionReceipt(BaseModel):
    """Durable record that a proof was verified and an action was executed (or refused)."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: ProtocolVersion
    receipt_id: Identifier
    proof_id: Identifier
    execution_attempt_id: Identifier
    execution_mode: ExecutionMode
    executed_at: Iso8601Timestamp
    outcome: ExecutionOutcome
    target: TargetRef
    action: ActionSpec
    provider_response_summary: dict | None = None
    refusal_id: Identifier | None = None
    evidence_links: list[EvidenceLink] = Field(default_factory=list)
    resource_signature: Signature | None = None
