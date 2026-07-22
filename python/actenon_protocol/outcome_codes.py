"""Execution outcome codes for ExecutionReceipt.outcome."""

from __future__ import annotations

from actenon_protocol._compat import StrEnum


class ExecutionOutcome(StrEnum):
    """The outcome of an execution attempt. Appears in ExecutionReceipt.outcome."""

    EXECUTED = "EXECUTED"
    REFUSED = "REFUSED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
