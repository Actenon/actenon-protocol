# Conformance

This directory contains the Actenon protocol conformance suite.

## Layout

```
conformance/
├── README.md           ← you are here
├── vectors/            ← test vectors (language-agnostic JSON)
│   ├── canonicalisation/
│   │   ├── valid/
│   │   └── invalid/
│   ├── proof/
│   │   ├── valid/
│   │   └── invalid/
│   ├── receipt/
│   │   ├── valid/
│   │   └── invalid/
│   ├── refusal/
│   │   ├── valid/
│   │   └── invalid/
│   └── execution-mode/
└── python/
    └── conformance_suite.py   ← pytest suite (Python reference)
```

## Running the Python suite

```bash
# From the repo root:
python -m pip install -e ".[dev]"
python -m pytest conformance/python/ -v
```

The suite tests:

1. **Canonicalisation** — every valid vector produces the exact expected bytes; every invalid vector raises `CanonicalisationError`.
2. **Schema validation** — every artefact vector is validated against its JSON Schema.
3. **Identifier validation** — canonical prefixes, aliases, forbidden prefixes, hex length, case.
4. **Refusal catalogue** — 20 canonical codes, alias resolution, disclosure policy, retryability.
5. **Execution modes** — both modes defined, mode explicit on every artefact, mode-mismatch produces `AUDIENCE_MISMATCH`.
6. **Version constants** — protocol version, canonicalisation profile, alias acceptance.
7. **Pydantic types** — every artefact type round-trips through JSON.
8. **ExecutionOutcome** — four outcome codes.

## Adding vectors

See `vectors/README.md`.

## Cross-language consistency

The TypeScript conformance suite is at `typescript/tests/conformance.test.ts`. It runs a subset of the Python suite (canonicalisation, identifiers, refusal codes, execution modes) and verifies byte-identical canonicalisation output.

A future Go and Rust port will run the same canonicalisation vectors. The protocol guarantees that all four implementations produce the same bytes for the same input.
