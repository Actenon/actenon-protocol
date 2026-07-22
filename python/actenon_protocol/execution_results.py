"""Execution result models — discriminated by mode.

This module mirrors ``schemas/execution_result.v1.json``. The two result
shapes (``BrokeredExecutionResult`` and ``ResourceOwnedExecutionResult``)
are NOT interchangeable; consumers MUST branch on ``mode`` before
reading mode-specific fields.

The dataclasses intentionally do not use inheritance — the
discriminated union is enforced by Python's type system at the
consumer's branch site, not by a shared base class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ._compat import StrEnum


class ExecutionMode(StrEnum):
    """The execution mode. Explicit on every proof, receipt, refusal, and SDK result."""

    BROKERED = "brokered"
    RESOURCE_OWNED = "resource_owned"


class BrokeredExecutionState(StrEnum):
    """Terminal state of a brokered execution."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUSED = "refused"
    OUTCOME_UNKNOWN = "outcome_unknown"


class ResourceOwnedExecutionState(StrEnum):
    """Terminal state of a resource-owned execution.

    ``submitted`` and ``accepted`` are NOT success states. Submission is
    not execution.
    """

    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REFUSED = "refused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    OUTCOME_UNKNOWN = "outcome_unknown"


class FinalityStatus(StrEnum):
    """Whether the result is authoritative or may change."""

    FINAL = "final"
    NON_FINAL = "non_final"


# Finality rules per state — single source of truth, used by both
# dataclass constructors and tests.
BROKERED_FINALITY: dict[BrokeredExecutionState, FinalityStatus] = {
    BrokeredExecutionState.SUCCEEDED: FinalityStatus.FINAL,
    BrokeredExecutionState.FAILED: FinalityStatus.FINAL,
    BrokeredExecutionState.REFUSED: FinalityStatus.FINAL,
    BrokeredExecutionState.OUTCOME_UNKNOWN: FinalityStatus.NON_FINAL,
}

RESOURCE_OWNED_FINALITY: dict[ResourceOwnedExecutionState, FinalityStatus] = {
    ResourceOwnedExecutionState.SUBMITTED: FinalityStatus.NON_FINAL,
    ResourceOwnedExecutionState.ACCEPTED: FinalityStatus.NON_FINAL,
    ResourceOwnedExecutionState.REFUSED: FinalityStatus.FINAL,
    ResourceOwnedExecutionState.SUCCEEDED: FinalityStatus.FINAL,
    ResourceOwnedExecutionState.FAILED: FinalityStatus.FINAL,
    ResourceOwnedExecutionState.OUTCOME_UNKNOWN: FinalityStatus.NON_FINAL,
}


class ExecutionResultValidationError(ValueError):
    """Raised when a result is constructed with contradictory fields."""


# ---------------------------------------------------------------------------
# Brokered result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BrokeredExecutionResult:
    """Result of a brokered execution.

    Hard rules enforced at construction:

      * ``state == SUCCEEDED`` requires ``provider_execution_observed == True``.
      * ``state == FAILED`` requires ``provider_execution_observed == True``.
      * ``state == OUTCOME_UNKNOWN`` requires ``finality == NON_FINAL``.
      * ``finality`` is derived from ``state``; passing a mismatched
        value raises ``ExecutionResultValidationError``.
    """

    state: BrokeredExecutionState
    verified_by: str
    executed_by: str
    provider_execution_observed: bool
    attempt_id: str
    occurred_at: str
    receipt_received: bool = False
    receipt_verified: bool = False
    provider_evidence: dict = field(default_factory=dict)
    reconciliation_status: str | None = None

    @property
    def mode(self) -> Literal["brokered"]:
        return "brokered"

    @property
    def finality(self) -> FinalityStatus:
        return BROKERED_FINALITY[self.state]

    def __post_init__(self) -> None:
        if self.state in (
            BrokeredExecutionState.SUCCEEDED,
            BrokeredExecutionState.FAILED,
        ) and not self.provider_execution_observed:
            raise ExecutionResultValidationError(
                f"brokered state {self.state.value!r} requires "
                "provider_execution_observed=True; refusing to "
                "report credential-resolution success as execution success"
            )
        if (
            self.state == BrokeredExecutionState.OUTCOME_UNKNOWN
            and self.finality != FinalityStatus.NON_FINAL
        ):
            raise ExecutionResultValidationError(
                "brokered outcome_unknown must be non_final"
            )


# ---------------------------------------------------------------------------
# Resource-owned result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResourceOwnedExecutionResult:
    """Result of a resource-owned execution.

    Hard rules enforced at construction:

      * ``state == SUCCEEDED`` requires ``resource_receipt_received == True``
        AND ``resource_receipt_verified == True`` AND
        ``provider_execution_observed == True``.
      * ``state == SUBMITTED`` requires ``provider_execution_observed == False``
        AND ``resource_receipt_received == False``.
      * ``state == ACCEPTED`` requires ``provider_execution_observed == False``.
      * ``finality`` is derived from ``state``; passing a mismatched
        value raises ``ExecutionResultValidationError``.
    """

    state: ResourceOwnedExecutionState
    verified_by: str
    executed_by: str
    attempt_id: str
    occurred_at: str
    provider_execution_observed: bool = False
    resource_receipt_received: bool = False
    resource_receipt_verified: bool = False
    resource_receipt: dict | None = None
    submission_reference: str | None = None

    @property
    def mode(self) -> Literal["resource_owned"]:
        return "resource_owned"

    @property
    def finality(self) -> FinalityStatus:
        return RESOURCE_OWNED_FINALITY[self.state]

    def __post_init__(self) -> None:
        if self.state == ResourceOwnedExecutionState.SUCCEEDED and not (
            self.provider_execution_observed
            and self.resource_receipt_received
            and self.resource_receipt_verified
        ):
            raise ExecutionResultValidationError(
                "resource_owned state 'succeeded' requires "
                "provider_execution_observed=True, "
                "resource_receipt_received=True, AND "
                "resource_receipt_verified=True; refusing to "
                "elevate submission or forged receipt to success"
            )
        if self.state == ResourceOwnedExecutionState.SUBMITTED and (
            self.provider_execution_observed or self.resource_receipt_received
        ):
            raise ExecutionResultValidationError(
                "resource_owned state 'submitted' requires "
                "provider_execution_observed=False AND "
                "resource_receipt_received=False; submission is "
                "not execution"
            )
        if self.state == ResourceOwnedExecutionState.ACCEPTED and self.provider_execution_observed:
            raise ExecutionResultValidationError(
                "resource_owned state 'accepted' requires "
                "provider_execution_observed=False; accepted "
                "means execution has not yet started"
            )


# ---------------------------------------------------------------------------
# Discriminated union
# ---------------------------------------------------------------------------


ExecutionResult = BrokeredExecutionResult | ResourceOwnedExecutionResult


def result_mode(result: ExecutionResult) -> ExecutionMode:
    """Return the mode of a result. Use this instead of ``isinstance``
    when serialising — it produces a stable string suitable for JSON."""
    if isinstance(result, BrokeredExecutionResult):
        return ExecutionMode.BROKERED
    return ExecutionMode.RESOURCE_OWNED


def serialise_result(result: ExecutionResult) -> dict:
    """Serialise a result to a JSON-safe dict matching the schema."""
    if isinstance(result, BrokeredExecutionResult):
        return {
            "mode": "brokered",
            "state": result.state.value,
            "finality": result.finality.value,
            "verified_by": result.verified_by,
            "executed_by": result.executed_by,
            "provider_execution_observed": result.provider_execution_observed,
            "receipt_received": result.receipt_received,
            "receipt_verified": result.receipt_verified,
            "attempt_id": result.attempt_id,
            "occurred_at": result.occurred_at,
            "provider_evidence": result.provider_evidence,
            "reconciliation_status": result.reconciliation_status,
        }
    return {
        "mode": "resource_owned",
        "state": result.state.value,
        "finality": result.finality.value,
        "verified_by": result.verified_by,
        "executed_by": result.executed_by,
        "provider_execution_observed": result.provider_execution_observed,
        "resource_receipt_received": result.resource_receipt_received,
        "resource_receipt_verified": result.resource_receipt_verified,
        "attempt_id": result.attempt_id,
        "occurred_at": result.occurred_at,
        "resource_receipt": result.resource_receipt,
        "submission_reference": result.submission_reference,
    }


__all__ = [
    "BROKERED_FINALITY",
    "BrokeredExecutionResult",
    "BrokeredExecutionState",
    "ExecutionMode",
    "ExecutionResult",
    "ExecutionResultValidationError",
    "FinalityStatus",
    "RESOURCE_OWNED_FINALITY",
    "ResourceOwnedExecutionResult",
    "ResourceOwnedExecutionState",
    "result_mode",
    "serialise_result",
]
