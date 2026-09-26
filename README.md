# Actenon Protocol

> The neutral, open, implementation-independent boundary contract for proof-bound consequential execution. Defines the wire shape every Actenon artefact speaks. Zero runtime dependencies. Any language, any framework, any cloud.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Version: v1.3.0](https://img.shields.io/badge/Version-v1.3.0-blue.svg)](CHANGELOG.md)
<!-- PYTHON-BADGE:START -->
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
<!-- PYTHON-BADGE:END -->
[![PyPI: actenon-protocol](https://img.shields.io/pypi/v/actenon-protocol?label=PyPI)](https://pypi.org/project/actenon-protocol/)
[![npm: @actenon/protocol-types](https://img.shields.io/npm/v/@actenon/protocol-types?label=npm)](https://www.npmjs.com/package/@actenon/protocol-types)
[![Zero dependencies](https://img.shields.io/badge/Dependencies-0-success.svg)](pyproject.toml)
[![CI](https://github.com/Actenon/actenon-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/Actenon/actenon-protocol/actions/workflows/ci.yml)
[![claims: machine-verified](https://img.shields.io/github/actions/workflow/status/Actenon/actenon-protocol/verify-claims.yml?branch=main&label=claims%3A%20machine-verified)](https://github.com/Actenon/actenon-protocol/actions/workflows/verify-claims.yml)
[![Code style: ruff](https://img.shields.io/badge/Code%20style-ruff-black.svg)](https://docs.astral.sh/ruff/)
[![Spec: stable](https://img.shields.io/badge/Spec-stable-success.svg)](protocol/)

### Every claim above is machine-verified

The `claims: machine-verified` badge links to a CI gate
([`verify-claims.yml`](.github/workflows/verify-claims.yml)) that fails on
every PR, push to `main`, and once a day if any factual claim this README
makes about the package stops being true:

- **Zero runtime dependencies** — read from `pyproject.toml`, not prose.
- **The vector count** — "129 hash-locked test vectors" is compared against
  the actual files in [`conformance/vectors/`](conformance/vectors/).
- **The hash lock** — every vector's SHA-256 is pinned in
  [`conformance/vectors.sha256`](conformance/vectors.sha256)
  (`sha256sum -c` format); a changed, deleted or unlisted vector fails
  [`scripts/check_vector_lock.py`](scripts/check_vector_lock.py).
- **The refusal catalogue** — the pre-compiled JSON the package ships is
  byte-checked against the human-editable YAML source of truth.
- **Install commands** — every `pip install` / `npm install` in this README
  is resolved against the live registry, and every `go get` module path is
  checked against the module's own `go.mod` on proxy.golang.org.
- **The ecosystem table** — rendered from [`ecosystem.yaml`](ecosystem.yaml),
  never hand-edited; the Python version badge is generated the same way.

If the badge is green, this README is telling the truth. If a claim drifts,
the badge goes red before a human notices.

---

## The Actenon ecosystem

The Protocol is one of the independent repositories that together close the **execution gap** — the gap between *upstream authorization* and the *execution edge* that actually performs a consequential side effect.

<!-- ECOSYSTEM-TABLE:START -->
| Repository | Role | Depends on | Packages |
|---|---|---|---|
| **`actenon-protocol`** ← you are here | The neutral wire contract — what every artefact looks like on the wire | — | `actenon-protocol` (PyPI) · `@actenon/protocol-types` (npm) |
| **`actenon-kernel`** | The open verifier — defines what a valid proof is | `actenon-protocol` | `actenon-kernel` (PyPI) |
| **`actenon-permit`** | The developer on-ramp and authority broker | `actenon-kernel`, `actenon-protocol` | `actenon-permit` (PyPI) · `@actenon/sdk` (npm) |
| **`actenon-scan`** | The independent static-analysis scanner | — | `actenon-scan` (PyPI) |
| **`sdk-go`** | Go verifier SDK — protected-endpoint proof verification in Go | `actenon-protocol` | [repo](https://github.com/Actenon/sdk-go) |
| **`sdk-rust`** | Rust verifier SDK — protected-endpoint proof verification in Rust | `actenon-protocol` | [repo](https://github.com/Actenon/sdk-rust) |

**Optional:** `actenon-cloud` — a managed control plane (private repository, not publicly available). Not required by any component above; every capability in this ecosystem works without it.
<!-- ECOSYSTEM-TABLE:END -->

The Protocol is the **only** Actenon package that the other repositories share as a common dependency (`actenon-scan` depends on none) — and even that is by choice, not by force. Every artefact defined here is implementable in any language with no runtime dependencies on any Actenon code.

---

## What this is

The Protocol defines the **wire format** that every Actenon component speaks. It is:

- **Neutral** — no runtime dependencies, no framework assumptions, no cloud requirement, no opinion on how you implement verification.
- **Versioned** — v1.3.0 (backward-compatible with v1.0.0–v1.2.0). Versioning policy in [`VERSIONING.md`](VERSIONING.md).
- **Cross-language** — Python (PyPI v1.3.0), TypeScript (npm v1.3.0), Go (`go get github.com/Actenon/sdk-go@v1.0.0`), and Rust (git dependency; crates.io pending) SDKs all conform to the same hash-locked conformance vectors. See [Multi-language SDKs](#multi-language-sdks--conformant-implementations) for the packaging status of each SDK.
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
| **`ExecutionProof`** (PCCB) | Cryptographic proof that a specific action was authorized for a specific audience, tenant, subject, target, scope, and time window. Single-use. | [`schemas/execution_proof.v1.json`](schemas/execution_proof.v1.json) |
| **`ExecutionReceipt`** | Durable record that a proof was verified and an action executed (or definitively refused before execution, in the refused-receipt path). | [`schemas/execution_receipt.v1.json`](schemas/execution_receipt.v1.json) |
| **`ExecutionRefusal`** | Structured refusal with two-layer disclosure (public-safe `disclosed_code` + trusted-only `internal_code`). | [`schemas/execution_refusal.v1.json`](schemas/execution_refusal.v1.json) |
| **`ExecutionResult`** | Discriminated union: `BrokeredExecutionResult \| ResourceOwnedExecutionResult` — disjoint field sets, no ambiguity. | [`schemas/execution_result.v1.json`](schemas/execution_result.v1.json) |
| **`BoundaryManifest`** | Declarative mapping from HTTP endpoints to canonical Actenon actions, with parameter extraction rules. | [`schemas/boundary_manifest.v1.json`](schemas/boundary_manifest.v1.json) |

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
canonicalisation: "ACTENON-JCS-STRICT-1"   # the only label for newly minted proofs and receipts
# "RFC8785-JCS" is accepted as a deprecated alias for historical proofs only.
# "actenon-jcs-sha256-v1" is REJECTED by every implementation.
```

This is a strict subset of RFC 8785 (JCS) with one deliberate difference:
object keys are sorted by UTF-8 bytes, not UTF-16 code units (the orders
differ only when U+E000–U+FFFF is compared with an astral character, so an
off-the-shelf RFC 8785 library is not conforming — see §4.1 of the profile).
It freezes:

- deterministic JSON canonicalisation (sorted keys, no insignificant whitespace)
- SHA-256 digesting
- **float rejection** — floating-point values are refused outright (model monetary/quantity values as integers or strings)
- Unicode and string handling — no normalisation; unpaired surrogates are rejected
- **duplicate JSON object keys are invalid** — runtime parsers must reject duplicates before canonicalisation
- base64url without padding where base64url is required
- 1 MiB max output, 32-level depth limit
- no in-place future changes

See [`canonicalisation/ACTENON-JCS-STRICT-1.md`](canonicalisation/ACTENON-JCS-STRICT-1.md). This profile is what makes action-hashes stable across Python, TypeScript, Go, and Rust implementations.

## Refusal taxonomy — two-layer disclosure

20 canonical refusal codes organised in a two-layer model:

- **`disclosed_code`** — public-safe code returned to untrusted callers. Every proof-validity failure collapses to the `PROOF_INVALID` umbrella; the other disclosed codes (`PROOF_EXPIRED`, `PROOF_NOT_YET_VALID`, `REPLAY_DETECTED`, `AUTHORITY_REVOKED`, `POLICY_REFUSAL`, `MALFORMED_REQUEST`, …) leak no cryptographic detail.
- **`internal_code`** — specific code disclosed only to trusted callers (`ISSUER_UNTRUSTED`, `SIGNATURE_INVALID`, `AUDIENCE_MISMATCH`, `TARGET_MISMATCH`, `ACTION_MISMATCH`, `PARAMETER_MISMATCH`). Legacy kernel/permit codes such as `TENANT_MISMATCH`, `SUBJECT_MISMATCH`, `BUDGET_EXCEEDED` and `RATE_LIMITED` are compatibility aliases that resolve to these (`resolve_alias`).

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
| **Python reference** | Stable v1.3.0 on PyPI | [`python/`](python/) — `pip install actenon-protocol` |
| **TypeScript types** | Stable v1.3.0 on npm | [`typescript/`](typescript/) — `npm install @actenon/protocol-types` |
| **Go SDK** | v1.0.0 — `go get github.com/Actenon/sdk-go@v1.0.0` | [`Actenon/sdk-go`](https://github.com/Actenon/sdk-go) |
| **Rust SDK** | v0.1.0 — git dependency or `cargo add --git` | [`Actenon/sdk-rust`](https://github.com/Actenon/sdk-rust) (crates.io publish pending token) |
| **OpenAPI 3.1 components** | Stable | [`openapi/components.yaml`](openapi/components.yaml) — drop into any OpenAPI-aware toolchain |
| **JSON Schemas** | Stable v1 | [`schemas/`](schemas/) — validate any artefact in any language |

**Honest status:** the wire protocol is fully cross-language — the
conformance vectors are hash-locked JSON that any language can pass. The
*packaging* is now at near-parity: Python and TypeScript are both at v1.3.0
on their respective registries. Go is at v1.0.0 and can be installed with
`go get github.com/Actenon/sdk-go@v1.0.0`. Rust is at v0.1.0 as a git
dependency (`cargo add --git https://github.com/Actenon/sdk-rust`);
crates.io publication is prepared (Cargo.toml has all required fields,
publish workflow is in place) and will complete once the
`CARGO_REGISTRY_TOKEN` secret is added to the sdk-rust repo.

Every implementation runs against the same hash-locked conformance vectors in [`conformance/vectors/`](conformance/vectors/). Conformance, not pedigree, decides validity.

## Install

```bash
pip install actenon-protocol
npm install @actenon/protocol-types
```

### Optional extras

The runtime package has **zero dependencies** — only the Python standard library.
Pydantic types, YAML loading, and conformance tooling are gated behind optional
extras so adopters who only need the wire contract pay no dependency cost:

```bash
pip install "actenon-protocol[types]"        # Pydantic models for the protocol shapes
pip install "actenon-protocol[yaml]"         # Direct YAML loading of the refusal catalogue
pip install "actenon-protocol[conformance]"  # jsonschema + rfc8785 for the conformance runner
pip install "actenon-protocol[all]"          # all of the above
```

## Use

```python
from actenon_protocol import (
    ExecutionMode,                 # "brokered" | "resource_owned"
    BrokeredExecutionState,        # succeeded | failed | refused | outcome_unknown
    ResourceOwnedExecutionState,   # submitted | accepted | refused | ...
    canonicalize_bytes,            # ACTENON-JCS-STRICT-1 canonicalisation (UTF-8 bytes)
    CanonicalisationError,
    RefusalCode,                   # the 20 canonical refusal codes
)
from actenon_protocol.types import (  # Pydantic models: pip install "actenon-protocol[types]"
    ExecutionProof,
    ExecutionReceipt,
    ExecutionRefusal,
)
# BoundaryManifest has no Python model; validate it with schemas/boundary_manifest.v1.json.

# Canonicalise any artefact deterministically. Raises CanonicalisationError on
# floats, NaN/Infinity, unpaired surrogates, depth > 32 or output > 1 MiB.
# Duplicate object keys cannot survive json.loads: reject them in your parser.
canonical_bytes = canonicalize_bytes({
    "action": "payment.refund",
    "target": "invoice:INV-7831",
    "amount_minor": 250000,   # integer minor units — never floats
    "currency": "USD",
})
```

## Conformance vectors

> **Looking for the canonical conformance map?** See
> [`CONFORMANCE.md`](CONFORMANCE.md) for the single page that maps the
> Protocol's 129 vectors and the Kernel's 51 vectors onto "what you must
> pass to claim what."

The protocol ships **129 hash-locked test vectors** across 6 categories:

| Category | Valid | Invalid | Total | What it tests |
|---|---:|---:|---:|---|
| `canonicalisation` | 22 | 15 | 37 | ACTENON-JCS-STRICT-1 (float rejection, duplicate keys, Unicode, depth/size limits) |
| `proof` | 15 | 14 | 29 | ExecutionProof schema, identifier prefixes, protocol version, required fields |
| `receipt` | 12 | 8 | 20 | ExecutionReceipt schema, outcome enum, both execution modes, required fields |
| `refusal` | 20 | 5 | 25 | All 20 refusal codes from the catalogue, two-layer disclosure, retryability |
| `execution-mode` | 10 | 0 | 10 | Mode distinction (brokered vs resource_owned), mode-specific constraints |
| `execution-result` | 4 | 4 | 8 | Discriminated union: disjoint field sets |
| **Total** | **83** | **46** | **129** | |

**129 vectors run on every PR** via the [CI workflow](.github/workflows/ci.yml), across Python 3.10 / 3.11 / 3.12, plus the TypeScript test suites (`typescript/` and `typescript-runtime/`).

### External implementations — earn "Actenon-compatible v1.3.0"

An external implementation is Actenon-compatible v1.3.0 if it accepts every valid vector and rejects every invalid vector. The [Runner Specification](conformance/RUNNER_SPEC.md) defines the interface, and the [standalone runner](conformance/runner.py) is a ready-to-use Python script that external implementations can subclass:

```bash
pip install -e ".[dev]"

# Run the conformance suite against the Python reference
python conformance/runner.py

# JSON output for CI integration
python conformance/runner.py --json

# Run a single category
python conformance/runner.py --category refusal
```

Vectors are generated by [`conformance/generate_vectors.py`](conformance/generate_vectors.py) for maintainability — regenerate with `python conformance/generate_vectors.py`. See [`conformance/README.md`](conformance/README.md) for details.

## Key guarantees

1. **Mode is explicit, never inferred** — on every proof, receipt, refusal, and result.
2. **Canonicalisation is deterministic** — `ACTENON-JCS-STRICT-1` (RFC 8785 subset), sorted keys, no whitespace, floats rejected, duplicate keys rejected.
3. **Refusal codes have two layers** — public-safe umbrella (`PROOF_INVALID`) + trusted detail (`AUDIENCE_MISMATCH`).
4. **Results are discriminated** — brokered and resource-owned results have disjoint field sets.
5. **Backward-compatible** — v1.3.0 is purely additive over v1.0.0–v1.2.0.
6. **Hash-locked** — conformance vectors are versioned and frozen.
7. **No ambient authority** — no field implies trust in an issuer, signer, or control plane. Trust is configured by the verifier.

## What's in this repo

```
protocol/            # Human-readable specs (00–12)
  00-versioning.md
  01-identifiers.md
  02-canonicalisation.md
  03-execution-modes.md
  04-claim-names.md
  05-proof.md
  06-receipt.md
  07-refusal.md
  08-outcome-codes.md
  ...
schemas/             # JSON Schemas (v1) — validate any artefact in any language
canonicalisation/    # ACTENON-JCS-STRICT-1 profile definition + test fixtures
identifiers/         # Identifier prefix registry (prefixes.v1.yaml)
refusals/            # Refusal-code catalogue (catalogue.v1.yaml)
conformance/         # Hash-locked conformance vectors + Python suite
python/              # Python reference implementation (pydantic models)
typescript/          # TypeScript types (@actenon/protocol-types)
typescript-runtime/  # Compiled TypeScript canonicaliser (@actenon/protocol)
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
