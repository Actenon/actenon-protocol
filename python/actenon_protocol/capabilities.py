"""Exact capabilities and the signed authority extension.

Scan names a power. Permit signs that name into a grant, then into one
concrete proof capability. The Kernel checks that capability against the
edge allow-list. A glob is a grant pattern, not a proof capability, and an
empty set is not filled in with the attempted action or with ``*``.

A proof token is not accepted because it is long, prefixed, or JSON. Those
are parsing. Acceptance needs a trust root and a signature that verifies.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

# Grant-scope metacharacters. A proof names concrete capabilities only.
GLOB_CHARS = frozenset("*?[]")


class CapabilityError(ValueError):
    """A capability set would widen, or an authority extension is unusable."""


def is_concrete_capability(value: object) -> bool:
    """True for one non-empty string that contains no glob character."""
    return isinstance(value, str) and bool(value) and not any(ch in value for ch in GLOB_CHARS)


def _require_concrete(capabilities: Sequence[str], *, empty_message: str) -> tuple[str, ...]:
    if isinstance(capabilities, (str, bytes)) or not isinstance(capabilities, Sequence):
        raise CapabilityError("capabilities must be a sequence of strings")
    if len(capabilities) == 0:
        raise CapabilityError(empty_message)
    concrete: list[str] = []
    for capability in capabilities:
        if not is_concrete_capability(capability):
            raise CapabilityError(
                "proof capability must name one concrete action; a wildcard is not a capability"
            )
        concrete.append(capability)
    return tuple(concrete)


def scope_capabilities_for_mint(capabilities: Sequence[str]) -> tuple[str, ...]:
    """The exact capabilities a proof may carry.

    An empty sequence is refused. It is not replaced by the attempted action
    or by ``*`` (that substitution is how an unnamed action became a proof).
    """
    return _require_concrete(
        capabilities,
        empty_message=(
            "empty allow-list cannot mint a proof; refusing to widen to the attempted action"
        ),
    )


def scope_capabilities_for_verification(
    declared: Sequence[str] | None,
    intent_capability: str,
) -> tuple[str, ...]:
    """The set E1 compares the intent's capability against.

    ``None`` means the caller passed no edge allow-list. The set is then
    exactly ``(intent_capability,)`` and is not a second allow-list. An
    empty sequence stays empty: it authorises nothing, and it is not
    replaced by the attempted action or by ``*``.
    """
    if not is_concrete_capability(intent_capability):
        raise CapabilityError(
            "intent capability must name one concrete action; a wildcard is not a capability"
        )
    if declared is not None and (
        isinstance(declared, (str, bytes)) or not isinstance(declared, Sequence)
    ):
        raise CapabilityError("capabilities must be a sequence of strings")
    if declared is None:
        return (intent_capability,)
    if len(declared) == 0:
        return ()
    return _require_concrete(
        declared,
        empty_message="empty edge allow-list authorises nothing",
    )


def capability_in_scope(capability: str, declared: Sequence[str]) -> bool:
    """Exact membership. Globs do not match, including a glob equal to itself."""
    if not is_concrete_capability(capability):
        return False
    return capability in declared and all(is_concrete_capability(item) for item in declared)


def authority_extension(*, issuer: str, grant_id: str, revocable: bool = True) -> dict[str, Any]:
    """The signed ``extensions`` object Permit embeds on a PCCB."""
    if not isinstance(issuer, str) or not issuer:
        raise CapabilityError("authority extension requires an issuer")
    if not isinstance(grant_id, str) or not grant_id:
        raise CapabilityError("authority extension requires a grant_id")
    if not isinstance(revocable, bool):
        raise CapabilityError("authority extension revocable must be a boolean")
    return {"authority": {"issuer": issuer, "grant_id": grant_id, "revocable": revocable}}


def parse_authority_extension(extensions: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Return ``extensions.authority``. Raises when it is missing or unusable."""
    if not isinstance(extensions, Mapping):
        raise CapabilityError("proof carries no authority extension")
    authority = extensions.get("authority")
    if not isinstance(authority, Mapping):
        raise CapabilityError("proof carries no authority extension")
    issuer = authority.get("issuer")
    grant_id = authority.get("grant_id")
    revocable = authority.get("revocable")
    if not isinstance(issuer, str) or not issuer:
        raise CapabilityError("authority extension requires an issuer")
    if not isinstance(grant_id, str) or not grant_id:
        raise CapabilityError("authority extension requires a grant_id")
    if not isinstance(revocable, bool):
        raise CapabilityError("authority extension revocable must be a boolean")
    return authority


def unauthenticated_refusal(*, trust_root_configured: bool, signature_verified: bool) -> str | None:
    """Refusal code when a token has not been cryptographically accepted.

    Returns None only when a trust root is configured and the signature
    verified. Token length, a ``v1.`` prefix, and well-formed JSON are not
    arguments: parsing is not acceptance. A verifier that reported any
    string of 16 or more characters as valid was non-conformant.
    """
    if not trust_root_configured:
        return "ISSUER_UNTRUSTED"
    if not signature_verified:
        return "SIGNATURE_INVALID"
    return None
