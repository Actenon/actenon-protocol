"""ExecutionRefusal pydantic model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from actenon_protocol.execution_modes import ExecutionMode
from actenon_protocol.refusal_codes import (
    DisclosurePolicy,
    is_detailed_code,
    is_disclosed_code_safe,
    refusal_to_disclosed_code,
    refusal_to_internal_code,
    refusal_to_retryable,
)
from actenon_protocol.types.common import (
    Identifier,
    Iso8601Timestamp,
    ProtocolVersion,
)
from actenon_protocol.types.evidence import EvidenceLink


class ExecutionRefusal(BaseModel):
    """Durable record that a proof was rejected or an action was refused.

    Carries a two-layer disclosure model: disclosed_code (public-safe) and
    optional internal_code (trusted-only).
    """

    model_config = ConfigDict(extra="forbid")

    protocol_version: ProtocolVersion
    refusal_id: Identifier
    proof_id: Identifier | None = None
    execution_attempt_id: Identifier | None = None
    execution_mode: ExecutionMode
    refused_at: Iso8601Timestamp
    disclosed_code: str
    internal_code: str | None = None
    message: str | None = None
    retryable: bool
    evidence_links: list[EvidenceLink] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_disclosure_consistency(self) -> ExecutionRefusal:
        # disclosed_code must be public-safe
        if not is_disclosed_code_safe(self.disclosed_code):
            raise ValueError(
                f"disclosed_code {self.disclosed_code!r} is not a public-safe code. "
                f"Public-safe codes are the umbrella codes that do not leak cryptographic detail."
            )
        # internal_code, if present, must be a detailed code
        if self.internal_code is not None and not is_detailed_code(self.internal_code):
            raise ValueError(
                f"internal_code {self.internal_code!r} is not a recognised detailed code."
            )
        # If internal_code is present, disclosed_code must be its umbrella
        if self.internal_code is not None:
            expected_disclosed = refusal_to_disclosed_code(
                self.internal_code, DisclosurePolicy.TRUSTED
            )
            if self.disclosed_code != expected_disclosed:
                raise ValueError(
                    f"disclosed_code {self.disclosed_code!r} does not match the umbrella "
                    f"for internal_code {self.internal_code!r} (expected {expected_disclosed!r})"
                )
        # retryable must match the catalogue
        expected_retryable = refusal_to_retryable(self.internal_code)
        if self.retryable != expected_retryable:
            raise ValueError(
                f"retryable {self.retryable!r} does not match the catalogue value "
                f"{expected_retryable!r} for internal_code {self.internal_code!r}"
            )
        return self

    @classmethod
    def from_internal_code(
        cls,
        *,
        refusal_id: str,
        internal_code: str | None,
        execution_mode: ExecutionMode,
        refused_at: str,
        policy: DisclosurePolicy,
        proof_id: str | None = None,
        execution_attempt_id: str | None = None,
        message: str | None = None,
        evidence_links: list | None = None,
        protocol_version: str = "1.0.0",
    ) -> ExecutionRefusal:
        """Construct an ExecutionRefusal from an internal_code and a disclosure policy.

        This is the recommended factory. It automatically computes the
        disclosed_code (per the policy), the retryable flag (per the catalogue),
        and validates consistency.
        """
        disclosed = refusal_to_disclosed_code(internal_code, policy)
        emitted_internal = refusal_to_internal_code(internal_code, policy)
        retryable = refusal_to_retryable(internal_code)
        return cls(
            protocol_version=protocol_version,
            refusal_id=refusal_id,
            proof_id=proof_id,
            execution_attempt_id=execution_attempt_id,
            execution_mode=execution_mode,
            refused_at=refused_at,
            disclosed_code=disclosed,
            internal_code=emitted_internal,
            message=message,
            retryable=retryable,
            evidence_links=evidence_links or [],
        )
