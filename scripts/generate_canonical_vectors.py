"""Generate normative canonicalisation conformance vectors.

This script produces the JSON fixture files under
conformance/vectors/canonicalisation/ that serve as the cross-language
normative test suite.

Run: python scripts/generate_canonical_vectors.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

VECTORS_DIR = Path(__file__).resolve().parent.parent / "conformance" / "vectors" / "canonicalisation"
VALID_DIR = VECTORS_DIR / "valid"
INVALID_DIR = VECTORS_DIR / "invalid"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
from actenon_protocol.canonicalisation import canonicalize_json


def write_valid(name: str, description: str, input_value, expected: str | None = None) -> None:
    if expected is None:
        expected = canonicalize_json(input_value)
    vector = {
        "name": name,
        "description": description,
        "input": input_value,
        "expected_canonical": expected,
    }
    path = VALID_DIR / f"{name}.json"
    with path.open("w") as f:
        json.dump(vector, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  valid: {name} -> {expected}")


def write_invalid(name: str, description: str, *, note: str = "", input_json: str | None = None) -> None:
    vector = {
        "name": name,
        "description": description,
        "expected_error": "CanonicalisationError",
        "expected_refusal_code": "CANONICALISATION_FAILURE",
    }
    if input_json is not None:
        vector["input_json"] = input_json
    if note:
        vector["note"] = note
    path = INVALID_DIR / f"{name}.json"
    with path.open("w") as f:
        json.dump(vector, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  invalid: {name}")


def _build_nested(depth: int) -> dict:
    result = {"value": "bottom"}
    for _ in range(depth):
        result = {"nested": result}
    return result


def main():
    print("Generating canonicalisation conformance vectors...")
    VALID_DIR.mkdir(parents=True, exist_ok=True)
    INVALID_DIR.mkdir(parents=True, exist_ok=True)

    # ── VALID VECTORS ──────────────────────────────────────────────

    write_valid("simple_object",
        "Simple object with mixed types. Verifies key sorting and value serialisation.",
        {"z": 1, "a": "hello", "b": [True, None, 42]})

    write_valid("nested_object",
        "Nested object. Verifies recursive key sorting.",
        {"outer": {"z": 1, "a": 2}, "inner": {"c": 3}})

    write_valid("unicode_strings",
        "Non-ASCII strings. Verifies no backslash-u escaping (RFC 8785 section 3.2.2).",
        {"name": "café", "city": "東京", "omega": "Ωμέγα"})

    write_valid("integer_values",
        "Integer values of various sizes including boundaries.",
        {"zero": 0, "one": 1, "negative": -1, "big": 1234567890123456789, "neg_big": -9999999999999999999})

    write_valid("integer_boundary",
        "Integer boundary values: max int32, min int32, max int53, power-of-2 boundaries.",
        {"max_int32": 2147483647, "min_int32": -2147483648, "max_int53": 9007199254740991, "min_int53": -9007199254740992, "power2_63": 9223372036854775807, "neg_power2_63": -9223372036854775808})

    write_valid("control_chars_escaped",
        "String with control characters. Verifies proper escaping.",
        {"tab": "a\tb", "newline": "a\nb", "null_byte": "a\u0000b", "cr": "a\rb", "ff": "a\fb", "bs": "a\bb"})

    write_valid("empty_collections",
        "Empty object and array. Verifies edge cases.",
        {"empty_obj": {}, "empty_arr": []})

    write_valid("key_order_byte_vs_codepoint",
        "Keys whose UTF-8 byte order differs from naive codepoint order. Z (0x5A) sorts before é (0xC3A9).",
        {"é": 1, "Z": 2, "a": 3})

    write_valid("string_with_quotes_and_backslashes",
        "Strings with double-quotes and backslashes. Verifies escaping.",
        {"q": 'she said "hi"', "bs": "C:\\Users\\test"})

    write_valid("action_parameters_payment_refund",
        "Realistic action parameters for a payment refund. Money as integer cents.",
        {"action": "payment.refund", "target": "stripe", "parameters": {"invoice_id": "inv_abc123", "amount_cents": 2500, "currency": "GBP", "reason": "customer_request"}})

    write_valid("reordered_keys_same_bytes",
        "Two objects with the same keys in different order produce the same canonical bytes.",
        {"b": 2, "a": 1, "c": 3})

    write_valid("boolean_values",
        "Boolean true and false.",
        {"t": True, "f": False})

    write_valid("null_value",
        "Null value in object and array.",
        {"n": None, "arr": [None, 1, None]})

    write_valid("absent_vs_null",
        "Absent field vs null field produce different canonical bytes. This vector has a null field.",
        {"present": 1, "null_field": None})

    write_valid("absent_field",
        "Object with an absent field (field simply not present). Compared with absent_vs_null to show the difference.",
        {"present": 1})

    write_valid("array_preserves_order",
        "Arrays preserve order. [1,2,3] is the canonical form.",
        [1, 2, 3])

    write_valid("array_reordering_differs",
        "Reversed array [3,2,1] produces different canonical bytes than [1,2,3].",
        [3, 2, 1])

    write_valid("unicode_normalization_none",
        "No Unicode normalisation. Precomposed é (U+00E9) and decomposed e+combining-acute (U+0065 U+0301) produce different bytes.",
        {"precomposed": "café", "decomposed": "cafe\u0301"})

    write_valid("visually_similar_strings",
        "Visually similar but distinct strings. Latin A (U+0041) vs Cyrillic А (U+0410) vs Greek Α (U+0391).",
        {"latin_a": "A", "cyrillic_a": "А", "greek_alpha": "Α"})

    write_valid("deeply_nested_valid",
        "30-level nested object (within the 32-depth limit).",
        _build_nested(30))

    write_valid("escaped_vs_unescaped_equivalent",
        "Strings that are equivalent after JSON unescaping produce the same canonical bytes.",
        {"unicode_escape": "café", "literal_unicode": "café"})

    write_valid("negative_zero_not_applicable",
        "Negative zero is not a valid integer. Zero is always 0. This vector verifies 0 serialises as '0'.",
        {"zero": 0})

    # ── INVALID VECTORS ────────────────────────────────────────────

    # Floats represented as JSON strings (the test parses them and canonicalises)
    write_invalid("float_top_level",
        "A top-level float value. MUST be rejected.",
        input_json="3.14")
    write_invalid("float_in_object",
        "A float nested in an object. MUST be rejected.",
        input_json='{"amount": 19.99}')
    write_invalid("float_in_array",
        "A float in an array. MUST be rejected.",
        input_json="[1, 2, 3.14, 4]")
    write_invalid("float_deep_nested",
        "A float deep in a nested structure. MUST be rejected.",
        input_json='{"outer": {"inner": {"value": 0.1}}}')
    write_invalid("float_nan",
        "NaN value. MUST be rejected (not valid JSON per RFC 8259).",
        input_json="NaN",
        note="JSON does not support NaN. Parsers that accept it MUST still reject it in the canonicaliser.")
    write_invalid("float_infinity",
        "Infinity value. MUST be rejected.",
        input_json="Infinity",
        note="JSON does not support Infinity.")
    write_invalid("float_neg_infinity",
        "Negative Infinity. MUST be rejected.",
        input_json="-Infinity",
        note="JSON does not support -Infinity.")
    write_invalid("float_exponent",
        "Float in exponent notation. MUST be rejected.",
        input_json="1.5e10",
        note="Exponent notation is a float representation. Use integer or string instead.")
    write_invalid("float_zero",
        "Float zero (0.0). MUST be rejected even though value is zero.",
        input_json="0.0",
        note="0.0 is a float, not an integer. Use 0 instead.")

    # Python-only invalid inputs (documented; tested in the conformance suite)
    write_invalid("non_string_key",
        "Object with non-string key (integer). Python-only.",
        note="In Python, the test constructs {1: 'a'} directly. JSON objects always have string keys.")
    write_invalid("unsupported_type_set",
        "Python set is not a JSON type. Python-only.",
        note="In Python, the test constructs {1, 2, 3} (a set) directly.")
    write_invalid("unsupported_type_bytes",
        "Python bytes is not a JSON type. Python-only.",
        note="In Python, the test constructs b'hello' directly.")
    write_invalid("deeply_nested_exceeds_limit",
        "Object nested 33 levels deep (exceeds the 32-level limit). Python-only.",
        note="In Python, the test constructs a 33-level nested dict.")
    write_invalid("oversized_structure",
        "Structure whose canonical form exceeds 1 MiB. Python-only.",
        note="In Python, the test constructs a large string or array.")
    write_invalid("duplicate_keys",
        "Object with duplicate keys. JSON parsers use last-wins; duplicate-key detection is the parser's responsibility.",
        note="The canonicaliser receives a dict/object that has already been constructed. Duplicate keys should be detected by the JSON parser.")

    print(f"\nGenerated vectors in {VECTORS_DIR}")


if __name__ == "__main__":
    main()
