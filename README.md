# Actenon Protocol

> The neutral, open, implementation-independent boundary contract for the Actenon ecosystem.

## What this is

The Protocol defines the **wire format** that every Actenon component speaks. It is:

- **Neutral** — no runtime dependencies, no framework assumptions, no cloud requirement.
- **Versioned** — v1.1.0 (backward-compatible with v1.0.0).
- **Cross-language** — Python reference, TypeScript SDK, Go SDK, Rust SDK all conform.
- **Hash-locked** — conformance vectors are versioned and locked.

## The artefacts

| Artefact | Purpose |
|---|---|
| `ExecutionProof` (PCCB) | Cryptographic proof that a specific action was authorised |
| `ExecutionReceipt` | Durable record that a proof was verified and an action executed |
| `ExecutionRefusal` | Structured refusal with two-layer disclosure (public-safe + trusted-only) |
| `ExecutionResult` | Discriminated union: `BrokeredExecutionResult \| ResourceOwnedExecutionResult` |
| `BoundaryManifest` | Declarative mapping from HTTP endpoints to canonical Actenon actions |

## Execution modes

| Mode | Who verifies | Who executes | Receipt issuer |
|---|---|---|---|
| `brokered` | In-stack Kernel verifier | Broker (Permit) | Broker |
| `resource_owned` | Resource boundary (independent Kernel) | Resource | Resource |

**Submission is not execution.** A `submitted` state is non-final. `succeeded` requires a cryptographically verified receipt.

## What's in this repo

```
protocol/           # Human-readable specs (01-12)
schemas/            # JSON Schemas (v1)
python/             # Python reference implementation
conformance/        # Hash-locked conformance vectors
typescript/         # TypeScript types (planned)
refusals/           # Refusal-code catalogue
identifiers/        # Identifier prefix registry
```

## Install

```bash
pip install actenon-protocol
```

## Use

```python
from actenon_protocol import (
    ExecutionMode,           # "brokered" | "resource_owned"
    BrokeredExecutionState,  # succeeded | failed | refused | outcome_unknown
    ResourceOwnedExecutionState,  # submitted | accepted | refused | ...
    canonicalize_json,       # JCS canonicalisation
    RefusalCode,             # 30+ structured refusal codes
)
```

## Key guarantees

1. **Mode is explicit, never inferred** — on every proof, receipt, refusal, and result.
2. **Canonicalisation is deterministic** — JCS (RFC 8785), sorted keys, no whitespace.
3. **Refusal codes have two layers** — public-safe umbrella (`PROOF_INVALID`) + trusted detail (`AUDIENCE_MISMATCH`).
4. **Results are discriminated** — brokered and resource-owned results have disjoint field sets.
5. **Backward-compatible** — v1.1.0 is purely additive over v1.0.0.

## Independence

This repo depends on **nothing**. Zero runtime dependencies. It can be adopted by any implementation in any language without pulling in Permit, Kernel, Cloud, or Scan.

## License

Apache-2.0
