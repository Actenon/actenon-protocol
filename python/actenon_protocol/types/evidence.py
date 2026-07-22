"""EvidenceLink pydantic model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from actenon_protocol.types.common import ActionHash, EvidenceLinkType, Iso8601Timestamp


class EvidenceTargetRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str | None = None
    hash: ActionHash | None = None
    inline_payload: dict | None = None


class EvidenceLink(BaseModel):
    """A reference to an external evidence record."""

    model_config = ConfigDict(extra="forbid")

    type: EvidenceLinkType
    link_type: Literal["inline", "external_url", "content_hash"]
    target_ref: EvidenceTargetRef
    issued_at: Iso8601Timestamp | None = None
    issuer_id: str | None = None
