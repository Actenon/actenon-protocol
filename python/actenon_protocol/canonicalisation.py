"""ACTENON-JCS-STRICT-1 canonicalisation reference implementation.

This is the Python reference for the Actenon protocol's canonicalisation
profile. The profile is a strict subset of RFC 8785 (JCS) that rejects
floating-point values entirely.

See canonicalisation/ACTENON-JCS-STRICT-1.md for the full specification.

The implementation produces byte-identical output to:
  - actenon-kernel/actenon/proof/canonical.py at commit 2b080d3
  - typescript/src/canonicalisation.ts in this repo (verified by the
    cross-language conformance suite)
"""

from __future__ import annotations

import json
from typing import Any, Final

from actenon_protocol.version import (
    ACCEPTED_CANONICALISATION_PROFILES,
)

# Hard limits. These match the actenon-kernel defaults.
MAX_CANONICAL_OUTPUT_BYTES: Final[int] = 1_048_576  # 1 MiB
MAX_JSON_DEPTH: Final[int] = 32


class CanonicalisationError(ValueError):
    """Raised when an input cannot be canonicalised under ACTENON-JCS-STRICT-1.

    The protocol refusal code for this is CANONICALISATION_FAILURE.
    """


def _validate_depth(value: Any, *, max_depth: int, current_depth: int = 0) -> None:
    if current_depth > max_depth:
        raise CanonicalisationError(f"JSON depth exceeds maximum {max_depth}")
    if isinstance(value, list):
        for item in value:
            _validate_depth(item, max_depth=max_depth, current_depth=current_depth + 1)
    elif isinstance(value, dict):
        for v in value.values():
            _validate_depth(v, max_depth=max_depth, current_depth=current_depth + 1)


def _utf8(value: str) -> bytes:
    """Return the UTF-8 bytes of `value`, rejecting unpaired surrogates.

    A lone surrogate (e.g. from ``json.loads('"\\ud800"')``) is not a Unicode
    scalar value and has no UTF-8 encoding (profile §4.2). It is a
    CanonicalisationError, never a silently substituted or escaped value.
    """
    try:
        # str.encode, not value.encode: a str subclass must not be able to
        # substitute different bytes (and so a different key order).
        return str.encode(value, "utf-8")
    except UnicodeEncodeError as e:
        raise CanonicalisationError(
            "strings must not contain unpaired UTF-16 surrogates "
            f"(found U+{ord(value[e.start]):04X}); they cannot be encoded as UTF-8"
        ) from None


def _canonicalize_string(value: str) -> str:
    _utf8(value)
    # ensure_ascii=False → non-ASCII chars are NOT \u-escaped (RFC 8785 §3.2.2)
    # separators=(",", ":") → no whitespace
    # allow_nan=False → reject NaN/Infinity
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _canonicalize_json(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int) and not isinstance(value, bool):
        # int.__repr__, not str(): subclasses (IntEnum on Python 3.10,
        # HTTPStatus, or any class overriding __str__) must serialise as
        # their integer value, never as "HTTPStatus.OK" or injected text.
        return int.__repr__(value)
    if isinstance(value, float):
        raise CanonicalisationError(
            "floating-point values are not supported in ACTENON-JCS-STRICT-1; "
            "use integer cents or string-encoded decimals instead"
        )
    if isinstance(value, str):
        return _canonicalize_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_canonicalize_json(item) for item in value) + "]"
    if isinstance(value, dict):
        # Reject non-string keys (RFC 8785 requires string keys)
        for key in value:
            if not isinstance(key, str):
                raise CanonicalisationError(
                    f"canonical JSON object keys must be strings, got {type(key).__name__}"
                )
        pieces = []
        for key in sorted(value.keys(), key=_utf8):
            pieces.append(_canonicalize_string(key) + ":" + _canonicalize_json(value[key]))
        return "{" + ",".join(pieces) + "}"
    raise CanonicalisationError(
        f"unsupported value type for canonicalization: {type(value).__name__}"
    )


def canonicalize_json(value: Any, *, max_depth: int = MAX_JSON_DEPTH) -> str:
    """Canonicalise `value` under ACTENON-JCS-STRICT-1. Returns the canonical string.

    Raises CanonicalisationError if:
      - the input contains a float
      - the input is too deep (depth > max_depth)
      - the input contains an unsupported type
      - the input contains non-string dict keys
    """
    _validate_depth(value, max_depth=max_depth)
    return _canonicalize_json(value)


def canonicalize_bytes(
    value: Any,
    *,
    max_depth: int = MAX_JSON_DEPTH,
    max_output_bytes: int = MAX_CANONICAL_OUTPUT_BYTES,
) -> bytes:
    """Canonicalise `value` and return the UTF-8 encoded bytes.

    Raises CanonicalisationError if:
      - any of the canonicalize_json error conditions are met
      - the canonical output exceeds max_output_bytes
    """
    if max_output_bytes <= 0:
        raise ValueError("max_output_bytes must be positive")
    canonical_str = canonicalize_json(value, max_depth=max_depth)
    canonical_bytes = canonical_str.encode("utf-8")
    if len(canonical_bytes) > max_output_bytes:
        raise CanonicalisationError(
            f"canonical output exceeds maximum {max_output_bytes} bytes "
            f"(got {len(canonical_bytes)} bytes)"
        )
    return canonical_bytes


def is_accepted_profile(label: str) -> bool:
    """Return True if `label` is an accepted canonicalisation profile label."""
    return label in ACCEPTED_CANONICALISATION_PROFILES


def assert_accepted_profile(label: str) -> None:
    """Raise CanonicalisationError if `label` is not an accepted profile label."""
    if not is_accepted_profile(label):
        raise CanonicalisationError(
            f"canonicalisation profile {label!r} is not accepted. "
            f"Accepted profiles: {sorted(ACCEPTED_CANONICALISATION_PROFILES)}"
        )
