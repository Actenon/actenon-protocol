"""Portable effect identities and outcomes; no policy or execution authority.

See protocol/15-consequential-effects.md. An identity is not permission to
execute. Only the protected edge's atomic reservation owner may execute.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from ._compat import StrEnum
from .canonicalisation import canonicalize_bytes
from .capabilities import is_concrete_capability

EFFECT_PROFILE = "ACTENON-EFFECT-1"
EFFECT_HASH_DOMAIN = b"ACTENON-EFFECT-1\x00"


class EffectError(ValueError):
    """Malformed effect descriptor or contradictory consequence evidence."""


class EffectOutcome(StrEnum):
    """Consequence certainty, separate from transport or provider status."""

    COMMITTED = "COMMITTED"
    NOT_EXECUTED = "NOT_EXECUTED"
    AMBIGUOUS = "AMBIGUOUS"


def effect_identity(descriptor: Mapping[str, Any]) -> str:
    """Hash a trusted adapter's canonical, fully scoped effect descriptor.

    ``exact`` includes all consequential parameters. ``semantic`` uses a
    reviewed key projection identifying the logical consequence, never an
    agent-selected idempotency key. Namespace is resource-owner configured.
    """
    if not isinstance(descriptor, Mapping):
        raise EffectError("effect descriptor must be an object")
    kind = descriptor.get("kind")
    field = (
        {"exact": "parameters", "semantic": "semantic_key"}.get(kind)
        if isinstance(kind, str)
        else None
    )
    if field is None or set(descriptor) != {
        "profile",
        "namespace",
        "kind",
        "action_type",
        "target",
        field,
    }:
        raise EffectError("effect descriptor has missing or unsupported fields")
    if descriptor["profile"] != EFFECT_PROFILE:
        raise EffectError("unsupported effect profile")
    namespace = descriptor["namespace"]
    if not isinstance(namespace, str) or not namespace or namespace != namespace.strip():
        raise EffectError("effect namespace must be a nonempty owner-configured identifier")
    if (
        not is_concrete_capability(descriptor["action_type"])
        or descriptor["action_type"] != descriptor["action_type"].strip()
    ):
        raise EffectError("effect action must be a concrete capability")
    target = descriptor["target"]
    if not isinstance(target, dict) or set(target) != {"type", "id"}:
        raise EffectError("effect target must be a canonical TargetRef")
    for value in target.values():
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or any(c in value for c in "*?[]")
        ):
            raise EffectError("effect target must be exact and nonempty")
    if not isinstance(descriptor[field], dict):
        raise EffectError("effect parameters/key must be an object")
    if kind == "semantic" and not descriptor[field]:
        raise EffectError("semantic effect key must be nonempty")
    payload = canonicalize_bytes(dict(descriptor))
    return "effect_" + hashlib.sha256(EFFECT_HASH_DOMAIN + payload).hexdigest()


def validate_effect_outcome(
    outcome: str, execution_occurred: bool | None, evidence_hash: str
) -> EffectOutcome:
    """Validate evidence shape, without asserting the evidence is authentic.

    A receipt signature and trusted boundary observation are still required.
    HTTP status alone cannot establish that a consequence committed.
    """
    try:
        result = EffectOutcome(outcome)
    except (ValueError, TypeError) as exc:
        raise EffectError("unknown effect outcome") from exc
    if execution_occurred is not None and type(execution_occurred) is not bool:
        raise EffectError("execution_occurred must be a boolean or null")
    if (
        not isinstance(evidence_hash, str)
        or len(evidence_hash) != 64
        or any(c not in "0123456789abcdef" for c in evidence_hash)
    ):
        raise EffectError("effect outcome requires a SHA256 evidence digest")
    if result == EffectOutcome.COMMITTED and execution_occurred is not True:
        raise EffectError("COMMITTED requires observed consequence execution")
    if result == EffectOutcome.NOT_EXECUTED and execution_occurred is not False:
        raise EffectError("NOT_EXECUTED requires established non-execution")
    if result == EffectOutcome.AMBIGUOUS and execution_occurred is False:
        raise EffectError("established non-execution is NOT_EXECUTED, not AMBIGUOUS")
    return result
