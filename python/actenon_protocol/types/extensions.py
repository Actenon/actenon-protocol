"""Signed proof extensions. Optional on ExecutionProof from wire 1.2.0."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AuthorityExtension(BaseModel):
    """The grant a proof was minted under.

    Permit signs ``{"issuer": "service:actenon-permit", "grant_id": "<id>",
    "revocable": true}``. Unknown extra members are preserved.
    """

    model_config = ConfigDict(extra="allow")

    issuer: str = Field(min_length=1)
    grant_id: str = Field(min_length=1)
    revocable: bool


class ProofExtensions(BaseModel):
    """Signed extension object. Unknown members are preserved."""

    model_config = ConfigDict(extra="allow")

    authority: AuthorityExtension | None = None
