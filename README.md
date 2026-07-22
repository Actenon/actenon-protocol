# Actenon Protocol

> The neutral, open, implementation-independent boundary contract for proof-bound consequential execution. Defines the wire shape every Actenon artefact speaks. Zero runtime dependencies. Any language, any framework, any cloud.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Version: v1.1.0](https://img.shields.io/badge/Version-v1.1.0-blue.svg)](CHANGELOG.md)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![PyPI: actenon-protocol](https://img.shields.io/pypi/v/actenon-protocol?label=PyPI)](https://pypi.org/project/actenon-protocol/)
[![TypeScript types v1.0.0](https://img.shields.io/badge/TypeScript%20types-v1.0.0%20(source)-orange.svg)](typescript/)
[![Zero dependencies](https://img.shields.io/badge/Dependencies-0-success.svg)](pyproject.toml)
[![CI](https://github.com/Actenon/actenon-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/Actenon/actenon-protocol/actions/workflows/ci.yml)
[![Code style: ruff](https://img.shields.io/badge/Code%20style-ruff-black.svg)](https://docs.astral.sh/ruff/)
[![Spec: stable](https://img.shields.io/badge/Spec-stable-success.svg)](SPEC.md)

---

## The Actenon ecosystem

The Protocol is one of five independent repositories that together close the **execution gap** — the gap between *upstream authorization* and the *execution edge* that actually performs a consequential side effect.

| Repo | Role | Depends on |
|---|---|---|
| **`actenon-protocol`** ← you are here | The neutral wire contract — what every artefact looks like on the wire | *nothing* |
| **`actenon-kernel`** | The open verifier — defines what a valid proof is | `actenon-protocol` |
| **`actenon-permit`** | The developer on-ramp + authority broker — issues grants, runs the PDP, brokers credentials | `actenon-kernel`, `actenon-protocol` |
| **`actenon-cloud`** | The optional managed control plane — multi-tenant, hosted, evidence bundles | `actenon-kernel`, `actenon-permit` |
| **`actenon-scan`** | The independent static-analysis scanner — finds the execution gap in any codebase | *nothing* |

The Protocol is the **only** repo the other four share as a common dependency — and even that is by choice, not by force. Every artefact defined here is implementable in any language with no runtime dependencies on any Actenon code.

---

## What this is

The Protocol defines the **wire format** that every Actenon component speaks. It is:

- **Neutral** — no runtime dependencies, no framework assumptions, no cloud requirement, no opinion on how you implement verification.
- **Versioned** — v1.1.0 (backward-compatible with v1.0.0). Versioning policy in [`VERSIONING.md`](VERSIONING.md).
- **Cross-language** — Python reference, TypeScript types, Go SDK, Rust SDK all conform to the same hash-locked conformance vectors.
- **Hash-locked** — conformance vectors are versioned and frozen; an implementation that passes v1.0.0 vectors will keep passing them forever.
- **Implementation-independent** — the same protocol can be implemented by Actenon, by a vendor, by an open-source competitor, or by an in-house team. Conformance, not pedigree, decides validity.

## Why it exists

Modern agent stacks have plenty of proof formats, capability tokens, and audit schemas — JWT, PASETO, UCAN, macaroons, OAuth tokens, SPIFFE SVIDs, custom audit JSON. None of them, however, are designed to answer the question the execution edge needs to answer:

> Is the exact consequential action about to execute still the exact action that was authorized — for this endpoint, this tenant, this subject, this target, this scope, this time window, and this single execution attempt?

The Protocol exists to give that question a **public, implementation-independent answer**. It defines:

- the request shape (`Action Intent`)
- the proof shape (`ExecutionProof`, a.k.a. PCCB — Proof of Constrained Capability Bound)
- the success shape (`ExecutionReceipt`)
- the failure shape (`ExecutionRefusal`)
- the discriminated result shape (`ExecutionResult`)
- the boundary-mapping shape (`BoundaryManifest`)

…and nothing else. It does not define how proof is issued, how policy is evaluated, how credentials are brokered, or how tenants are managed. Those are intentionally left to the implementer.

## The five artefacts

| Artefact | Purpose | Schema |
|---|---|---|
| **`ExecutionProof`** (PCCB) | Cryptographic proof that a specific action was authorized for a specific audience, tenant, subject, target, scope, and time window. Single-use. | [`schemas/execution-proof.schema.json`](schemas/execution-proof.schema.json) |
| **`ExecutionReceipt`** | Durable record that a proof was verified and an action executed (or definitively refused before execution, in the refused-receipt path). | [`schemas/execution-receipt.schema.json`](schemas/execution-receipt.schema.json) |
| **`ExecutionRefusal`** | Structured refusal with two-layer disclosure (public-safe `disclosed_code` + trusted-only `internal_code`). | [`schemas/execution-refusal.schema.json`](schemas/execution-refusal.schema.json) |
| **`ExecutionResult`** | Discriminated union: `BrokeredExecutionResult \| ResourceOwnedExecutionResult` — disjoint field sets, no ambiguity. | [`schemas/execution-result.schema.json`](schemas/execution-result.schema.json) |
| **`BoundaryManifest`** | Declarative mapping from HTTP endpoints to canonical Actenon actions, with parameter extraction rules. | [`schemas/boundary-manifest.schema.json`](schemas/boundary-manifest.schema.json) |

## The two execution modes

| Mode | Who verifies | Who executes | Receipt issuer | When to use |
|---|---|---|---|---|
| `brokered` | In-stack Kernel verifier (typically inside the agent framework) | Broker (Permit) — credentials resolved server-side after verification | Broker | You control the agent framework and want credentials never to reach the agent |
| `resource_owned` | Resource boundary (independent Kernel verifier) | The resource itself (FastAPI route, Express endpoint, Go handler) | Resource | You cannot fully trust the agent, or the resource is shared by multiple callers, or the resource team is a separate org |

**Submission is not execution.** A `submitted` state is non-final. `succeeded` requires a cryptographically verified receipt. The protocol enforces this distinction with disjoint result field sets — brokered and resource-owned results cannot be confused.

The mode is **explicit, never inferred** — it appears on every proof, receipt, refusal, and result. There is no "default mode."

## Canonicalisation profile — `ACTENON-JCS-STRICT-1`

Every signed and digested artefact in the protocol uses the same canonicalisation profile:

```yaml
canonicalization_profile: "actenon-jcs-sha256-v1"   # cross-repo wire contract name
canonicalization_label:  "ACTENON-JCS-STRICT-1"      # protocol-canonical label
```

This is a strict subset of RFC 8785 (JCS). It freezes:

- deterministic JSON canonicalisation (sorted keys, no insignificant whitespace)
- SHA-256 digesting
- **float rejection** — floating-point values are refused outright (model monetary/quantity values as integers or strings)
- Unicode and string handling
- **duplicate JSON object keys are invalid** — runtime parsers must reject duplicates before canonicalisation
- base64url without padding where base64url is required
- 1 MiB max output, 32-level depth limit
- no in-place future changes

See [`canonicalisation/ACTENON-JCS-STRICT-1.md`](canonicalisation/ACTENON-JCS-STRICT-1.md). This profile is what makes action-hashes stable across Python, TypeScript, Go, and Rust implementations.

## Refusal taxonomy — two-layer disclosure

20 canonical refusal codes organised in a two-layer model:

- **`disclosed_code`** — public-safe umbrella code returned to untrusted callers. Always collapses to one of a small set (`PROOF_INVALID`, `REPLAY_DETECTED`, `UNAUTHORIZED`, `FORBIDDEN`, `ACTION_REFUSED`).
- **`internal_code`** — specific code disclosed only to trusted callers (`AUDIENCE_MISMATCH`, `ACTION_MISMATCH`, `TENANT_MISMATCH`, `SUBJECT_MISMATCH`, `EXPIRED`, `NOT_YET_VALID`, `REVOKED`, `SCOPE_EXCEEDED`, `BUDGET_EXCEEDED`, `RATE_LIMITED`, `APPROVAL_REQUIRED`, `PARAMETER_DIGEST_MISMATCH`, etc.)

This prevents an attacker from probing the verifier by enumerating refusal codes, while still giving operators the specific information they need to debug. Full catalogue in [`refusals/catalogue.v1.yaml`](refusals/catalogue.v1.yaml).

## Identifier prefixes

The protocol reserves a small set of identifier prefixes so any artefact is recognisable across implementations:

| Prefix | Artefact |
|---|---|
| `intent_` | Action Intent |
| `authz_` | Authorised Execution Intent |
| `grant_` | Grant (capability token) |
| `proof_` | ExecutionProof / PCCB |
| `exec_` | Execution attempt |
| `rcpt_` | ExecutionReceipt |
| `rful_` | ExecutionRefusal |

See [`identifiers/prefixes.v1.yaml`](identifiers/prefixes.v1.yaml).

## Multi-language SDKs & conformant implementations

| Implementation | Status | Path |
|---|---|---|
| **Python reference** | Stable v1.1.0 on PyPI | [`python/`](python/) — `pip install actenon-protocol` |
| **TypeScript types** | v1.0.0 (source — npm publish pending) | [`typescript/`](typescript/) — `@actenon/protocol-types` |
| **Go SDK** | Conformant | in `actenon-kernel` `sdk/go/` |
| **Rust SDK** | Conformant | in `actenon-kernel` `sdk/rust/` |
| **OpenAPI 3.1 components** | Stable | [`openapi/components.yaml`](openapi/components.yaml) — drop into any OpenAPI-aware toolchain |
| **JSON Schemas** | Stable v1 | [`schemas/`](schemas/) — validate any artefact in any language |

Every implementation runs against the same hash-locked conformance vectors in [`conformance/vectors/`](conformance/vectors/). Conformance, not pedigree, decides validity.

## Install

```bash
pip install actenon-protocol
```

TypeScript types are at v1.0.0 in [`typescript/`](typescript/) — hand-written types matching the JSON Schemas. Built and tested in CI; **not yet published to npm**. Install from source:

```bash
git clone https://github.com/Actenon/actenon-protocol.git
cd actenon-protocol/typescript
npm install && npm run build
npm link                              # then `npm link @actenon/protocol-types` in your project
```

## Use

```python
from actenon_protocol import (
    ExecutionMode,                 # "brokered" | "resource_owned"
    BrokeredExecutionState,        # succeeded | failed | refused | outcome_unknown
    ResourceOwnedExecutionState,   # submitted | accepted | refused | ...
    canonicalize_json,             # ACTENON-JCS-STRICT-1 canonicalisation
    RefusalCode,                   # 20+ structured refusal codes
    ExecutionProof,
    ExecutionReceipt,
    ExecutionRefusal,
    BoundaryManifest,
)

# Canonicalise any artefact deterministically (raises on floats / duplicate keys)
canonical_bytes = canonicalize_json({
    "action": "payment.refund",
    "target": "invoice:INV-7831",
    "amount_minor": 250000,   # integer minor units — never floats
    "currency": "USD",
})
```

## Conformance vectors

The protocol ships hash-locked valid and invalid fixtures for:

- canonicalisation (valid, float-rejected, duplicate-key-rejected, depth-limit, size-limit)
- proof structure & signature
- receipt structure & state transitions
- refusal code catalogue & two-layer disclosure
- execution-mode distinction (brokered vs resource-owned, disjoint field sets)

**117 vectors run on every PR** via the [CI workflow](.github/workflows/ci.yml), across Python 3.10 / 3.11 / 3.12, plus the TypeScript conformance suite (21 tests). Run locally:

```bash
pip install -e ".[dev]"
python -m pytest conformance/python/ -v          # 117 pass, 21 skipped
cd typescript && bun install && bun test          # 21 pass, 40 expect() calls
```

If your implementation passes these vectors, you conform to v1.1.0. If it does not, you don't. See [`conformance/`](conformance/).

## Key guarantees

1. **Mode is explicit, never inferred** — on every proof, receipt, refusal, and result.
2. **Canonicalisation is deterministic** — `ACTENON-JCS-STRICT-1` (RFC 8785 subset), sorted keys, no whitespace, floats rejected, duplicate keys rejected.
3. **Refusal codes have two layers** — public-safe umbrella (`PROOF_INVALID`) + trusted detail (`AUDIENCE_MISMATCH`).
4. **Results are discriminated** — brokered and resource-owned results have disjoint field sets.
5. **Backward-compatible** — v1.1.0 is purely additive over v1.0.0.
6. **Hash-locked** — conformance vectors are versioned and frozen.
7. **No ambient authority** — no field implies trust in an issuer, signer, or control plane. Trust is configured by the verifier.

## What's in this repo

```
protocol/            # Human-readable specs (01–12)
  01-action-intent.md
  02-execution-proof.md
  03-execution-modes.md
  04-execution-receipt.md
  05-execution-refusal.md
  06-boundary-manifest.md
  07-canonicalisation.md
  08-outcome-codes.md
  ...
schemas/             # JSON Schemas (v1) — validate any artefact in any language
canonicalisation/    # ACTENON-JCS-STRICT-1 profile definition + test fixtures
identifiers/         # Identifier prefix registry (prefixes.v1.yaml)
refusals/            # Refusal-code catalogue (catalogue.v1.yaml)
conformance/         # Hash-locked conformance vectors + Python suite
python/              # Python reference implementation (pydantic models)
typescript/          # TypeScript types (@actenon/protocol-types)
openapi/             # OpenAPI 3.1 components
```

## Integration guide

For the full adoption path — including how to wire the protocol into an existing service without pulling in any other Actenon repo — see [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md). The short version: install this package, validate every incoming `Action Intent` + `ExecutionProof` against the JSON Schemas, canonicalise with `canonicalize_json`, and verify the proof signature against your configured issuer keys. That alone gives you protocol-conformant refusal — even before you adopt the Kernel, Permit, or Cloud.

## What the Protocol does NOT do

- Issue grants or proofs (that's Permit's job, or any compliant issuer's job).
- Verify proofs (that's the Kernel's job, or any compliant verifier's job).
- Execute provider calls (that's the broker/adapter's job).
- Manage tenants, approvals, evidence, or audit (that's Cloud's job, or your own).
- Make any trust claim about the issuer, signer, or control plane.
- Provide a hosted transparency log (the artefact shape exists; the operation is separate).

The Protocol is the contract. It is deliberately the smallest, most boring, most implementable thing in the ecosystem — because that is exactly what a wire contract needs to be.

## Independence

This repo depends on **nothing**. Zero runtime dependencies. It can be adopted by any implementation in any language without pulling in Permit, Kernel, Cloud, or Scan. Conformance is the only claim an implementation needs to make.

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
