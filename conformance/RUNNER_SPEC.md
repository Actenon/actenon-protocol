# Conformance Runner Specification

This document specifies how an external implementation of the Actenon
protocol can run the conformance vectors and claim
**"Actenon-compatible v1.5.0"**.

## What "Actenon-compatible" means

An implementation is Actenon-compatible v1.5.0 if, and only if, it:

1. **Accepts** every vector in `conformance/vectors/*/valid/` as valid
   (schema-constructable, no validation errors).
2. **Rejects** every vector in `conformance/vectors/*/invalid/` as invalid
   (schema error, pydantic error, or identifier error — depending on the
   vector's `expected_refusal_code`).
3. **Canonicalises** every canonicalisation vector to the exact
   `expected_canonical` bytes specified in the vector.
4. **Distinguishes** execution modes correctly — `brokered` and
   `resource_owned` fields are disjoint, and mode-specific constraints
   (e.g. brokered-succeeded-requires-observation) are enforced.
5. **Maps** refusal codes correctly — `disclosed_code` is always
   public-safe, `internal_code` maps to the correct umbrella, and
   `retryable` matches the catalogue.

## Vector format

Every vector is a JSON file with this top-level shape:

```json
{
  "name": "unique_vector_name",
  "description": "Human-readable description of what this vector tests.",
  "artefact": { ... },           // the artefact to validate
  "expected_validation": "valid" | "invalid"
}
```

Invalid vectors also carry:

```json
{
  "expected_refusal_code": "MISSING_REQUIRED_FIELD"  // why it should fail
}
```

Canonicalisation vectors carry:

```json
{
  "input": { ... },               // the JSON value to canonicalise
  "expected_canonical": "{...}"   // the exact canonical bytes
}
```

Execution-mode vectors carry:

```json
{
  "input": { ... },               // the mode/result to check
  "expected_validation": "valid" | "invalid",
  "expected_error": "SCHEMA_INVALID",  // if invalid
  "expected_finality": "final" | "non_final"  // for state checks
}
```

## How to write a runner

An external implementation provides a **runner** — a script or program
that loads every vector, feeds it to the implementation's validation
API, and reports pass/fail per vector.

### Python runner example

The reference implementation ships a runner as `conformance/runner.py`
(`python conformance/runner.py`). To run it against your own
implementation, load it and subclass `ReferenceValidator` (or implement
every method of the `Validator` protocol), overriding the methods your
implementation provides:

```python
import importlib.util, sys

spec = importlib.util.spec_from_file_location("runner", "conformance/runner.py")
runner = importlib.util.module_from_spec(spec)
sys.modules["runner"] = runner
spec.loader.exec_module(runner)

class MyValidator(runner.ReferenceValidator):
    def validate_proof(self, artefact: dict) -> tuple[bool, str | None]: ...
    def validate_receipt(self, artefact: dict) -> tuple[bool, str | None]: ...
    def validate_refusal(self, artefact: dict) -> tuple[bool, str | None]: ...
    def validate_execution_result(self, artefact: dict) -> tuple[bool, str | None]: ...
    def canonicalize(self, input_value) -> str: ...      # raise on forbidden input
    def parse_json(self, text: str): ...                 # raise on duplicate keys / NaN
    def language_specific_input(self, vector_name: str):
        return runner.NOT_APPLICABLE                     # if your language has no set/bytes/int keys

results = runner.ConformanceRunner(MyValidator()).run_all()
print(f"Passed: {results.passed}  Failed: {results.failed}  Skipped: {results.skipped}")
for failure in results.failures:
    print(f"  FAIL: {failure.vector.category}/{failure.vector.name}: {failure.reason}")
```

Every vector is executed. Invalid canonicalisation vectors pass only if
your implementation refuses the input (in `parse_json` or `canonicalize`);
language-specific ones your language cannot express are reported as
**skipped**, never as passed.

### Non-Python runners

For implementations in other languages (Go, Rust, TypeScript, etc.):

1. Read every `*.json` file under `conformance/vectors/` (verify them first:
   `cd conformance/vectors && sha256sum -c ../vectors.sha256`).
2. For each artefact vector, call your implementation's validation API with
   the `artefact` (or `input` for execution-mode vectors).
3. Compare the result to `expected_validation` (`expected_valid` for
   `execution-result` vectors):
   - `valid` / `true` → your implementation must accept it (no error).
   - `invalid` / `false` → your implementation must reject it (error).
4. For valid canonicalisation vectors, compare your canonical output to
   `expected_canonical` byte-for-byte.
5. For invalid canonicalisation vectors, parse `input_json` with the parser
   you use for untrusted input and canonicalise the result: one of the two
   steps MUST fail. `duplicate_keys` has no `input_json`; use
   `{"a": 1, "a": 2}`. `oversized_structure` is a string of 1,048,576 `x`
   characters. `non_string_key`, `unsupported_type_set` and
   `unsupported_type_bytes` only apply where the language can express them.
6. If all vectors pass, your implementation is Actenon-compatible v1.5.0.

## Vector inventory

| Category | Valid | Invalid | Total | What it tests |
|---|---:|---:|---:|---|
| `canonicalisation` | 22 | 15 | 37 | ACTENON-JCS-STRICT-1 canonicalisation (float rejection, duplicate keys, Unicode, depth/size limits) |
| `proof` | 15 | 14 | 29 | ExecutionProof schema, identifier prefixes, protocol version, canonicalisation profile, required fields |
| `receipt` | 12 | 8 | 20 | ExecutionReceipt schema, outcome enum, required fields, both execution modes |
| `refusal` | 20 | 5 | 25 | All 20 refusal codes from the catalogue, two-layer disclosure, retryability, code-to-umbrella mapping |
| `execution-mode` | 10 | 0 | 10 | Mode distinction (brokered vs resource_owned), mode-specific field constraints, finality |
| `execution-result` | 4 | 4 | 8 | Discriminated union: disjoint field sets for brokered vs resource-owned results |
| **Total** | **83** | **46** | **129** | |

## Regenerating vectors

Vectors are generated by `conformance/generate_vectors.py`. To regenerate:

```bash
python conformance/generate_vectors.py
```

The generator produces proof, receipt, refusal, and execution-mode vectors.
Canonicalisation and execution-result vectors are hand-authored and
committed directly.

## Versioning

- **Vector format**: v1 (the `.v1.json` suffix on every file).
- **Catalogue version**: 1 (from `refusals/catalogue.v1.yaml`).
- **Protocol version**: v1.2.0.

New vectors MAY be added in point releases. Existing vectors WILL NOT be
removed or have their expected results changed within protocol v1.x.
