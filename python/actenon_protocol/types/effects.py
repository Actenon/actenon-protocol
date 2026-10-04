"""Typed portable effect reference and consequence evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from actenon_protocol.effects import validate_effect_outcome


class EffectReference(BaseModel):
    """Signed ledger reference; it does not itself reserve or authorize an effect."""

    model_config = ConfigDict(extra="forbid", strict=True)
    profile: Literal["ACTENON-EFFECT-1"]
    effect_id: str = Field(pattern=r"^effect_[0-9a-f]{64}$")
    reservation_id: str = Field(pattern=r"^reservation_[0-9a-f]{32}$")
    owner_attempt_id: str = Field(pattern=r"^exec_[0-9a-f]{16,}$")


class EffectEvidence(EffectReference):
    """Effect record signed as part of an execution receipt's evidence link."""

    outcome: Literal["COMMITTED", "NOT_EXECUTED", "AMBIGUOUS"]
    execution_occurred: bool | None
    evidence_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def evidence_is_consistent(self) -> EffectEvidence:
        validate_effect_outcome(self.outcome, self.execution_occurred, self.evidence_hash)
        return self
