"""AuthorisedExecutionIntent pydantic model.

Note: the protocol only defines the wire shape of the intent. The complete
lifecycle (approval, attenuation, persistence) is owned by the authority
broker (e.g. actenon-permit) and Cloud — NOT by this protocol.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from actenon_protocol.execution_modes import ExecutionMode
from actenon_protocol.types.common import (
    ActionSpec,
    Identifier,
    Iso8601Timestamp,
    ProtocolVersion,
    TargetRef,
)


class AuthorisedExecutionIntent(BaseModel):
    """The developer-facing claim that an agent wants to perform an action.

    NOT the boundary artefact (that is ExecutionProof). The intent is what
    the proof is bound to.
    """

    model_config = ConfigDict(extra="forbid")

    protocol_version: ProtocolVersion
    intent_id: Identifier
    subject: str
    action: ActionSpec
    target: TargetRef
    requested_at: Iso8601Timestamp
    requested_expiry: Iso8601Timestamp | None = None
    requested_execution_mode: ExecutionMode | None = None
    metadata: dict | None = None
