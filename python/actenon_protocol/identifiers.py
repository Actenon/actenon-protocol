"""Identifier validation, generation, and alias resolution.

Implements the identifier format defined in:
  - protocol/01-identifiers.md
  - identifiers/prefixes.v1.yaml

Format: <prefix><hex_chars>
  - prefix is lowercase, matches ^[a-z][a-z0-9_]*_$
  - hex_chars is lowercase hexadecimal, minimum 16 chars, recommended 32
  - full regex: ^[a-z][a-z0-9_]*_[0-9a-f]{16,}$
"""

from __future__ import annotations

import os
import re
from typing import Final

# Canonical prefixes for protocol v1.x.
# Source of truth: identifiers/prefixes.v1.yaml
PREFIXES: Final[frozenset[str]] = frozenset(
    {
        "intent_",
        "authz_",
        "grant_",
        "proof_",
        "exec_",
        "rcpt_",
        "rful_",
    }
)

# Aliases: identifiers with these prefixes are accepted as equivalent to
# identifiers with the corresponding canonical prefix.
ALIASES: Final[dict[str, str]] = {
    "act_": "intent_",  # actenon-permit's Action.action_id, passed as intent_id
    "pccb_": "proof_",  # defensive — no known wire emission, but kernel uses pccb_id internally
}

# Forbidden prefixes: MUST NOT be used. Reserved for out-of-scope concerns.
FORBIDDEN_PREFIXES: Final[frozenset[str]] = frozenset(
    {
        "tenant_",
        "user_",
        "policy_",
        "approval_",
    }
)

# Full identifier regex.
# - prefix: lowercase letters/digits/underscore, ending in underscore
# - hex: lowercase hexadecimal, minimum 16 chars
_IDENTIFIER_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<prefix>[a-z][a-z0-9_]*_)(?P<hex>[0-9a-f]{16,})$"
)

# Recommended hex length for newly-generated identifiers (UUID4 hex = 32).
RECOMMENDED_HEX_LENGTH: Final[int] = 32

# Minimum hex length (preserves backward compatibility with existing
# actenon-permit identifiers, which use 16 hex chars).
MINIMUM_HEX_LENGTH: Final[int] = 16


def is_valid_identifier(value: str) -> bool:
    """Return True if `value` is a valid Actenon protocol identifier.

    A valid identifier matches the regex and uses either a canonical prefix
    or a registered alias. Forbidden prefixes are rejected.
    """
    if not isinstance(value, str):
        return False
    match = _IDENTIFIER_RE.match(value)
    if match is None:
        return False
    prefix = match.group("prefix")
    if prefix in FORBIDDEN_PREFIXES:
        return False
    if prefix in PREFIXES:
        return True
    if prefix in ALIASES:
        return True
    # Unknown prefix: accept (forward compatibility — the prefix is
    # informative, not authoritative). The hex must still match the regex.
    # The regex already enforced this.
    return True


def normalise_identifier(value: str) -> str:
    """Return the canonical form of `value`.

    If `value` uses an alias prefix, the canonical prefix is substituted.
    Otherwise `value` is returned unchanged.

    Raises ValueError if `value` is not a valid identifier.
    """
    if not is_valid_identifier(value):
        raise ValueError(f"not a valid Actenon identifier: {value!r}")
    match = _IDENTIFIER_RE.match(value)
    assert match is not None  # is_valid_identifier guaranteed this
    prefix = match.group("prefix")
    hex_chars = match.group("hex")
    canonical_prefix = ALIASES.get(prefix, prefix)
    return f"{canonical_prefix}{hex_chars}"


def generate_identifier(prefix: str, *, hex_length: int = RECOMMENDED_HEX_LENGTH) -> str:
    """Generate a fresh identifier with the given prefix.

    Uses os.urandom for cryptographic randomness. The default hex_length
    is 32 (UUID4 hex, 128 bits of entropy).

    Raises ValueError if `prefix` is not a registered canonical prefix.
    """
    if prefix not in PREFIXES:
        raise ValueError(
            f"prefix {prefix!r} is not a registered canonical prefix. "
            f"Use one of: {sorted(PREFIXES)}"
        )
    if hex_length < MINIMUM_HEX_LENGTH:
        raise ValueError(f"hex_length {hex_length} is below minimum {MINIMUM_HEX_LENGTH}")
    # Generate ceil(hex_length / 2) random bytes.
    num_bytes = (hex_length + 1) // 2
    random_bytes = os.urandom(num_bytes)
    hex_chars = random_bytes.hex()[:hex_length]
    return f"{prefix}{hex_chars}"


def get_prefix(value: str) -> str | None:
    """Return the prefix of `value`, or None if not a valid identifier."""
    if not is_valid_identifier(value):
        return None
    match = _IDENTIFIER_RE.match(value)
    assert match is not None
    return match.group("prefix")


def get_canonical_prefix(value: str) -> str | None:
    """Return the canonical prefix of `value` (resolving aliases), or None."""
    prefix = get_prefix(value)
    if prefix is None:
        return None
    return ALIASES.get(prefix, prefix)
