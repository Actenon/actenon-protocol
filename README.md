# actenon-protocol

> The neutral, open, implementation-independent boundary contract for the Actenon ecosystem and compatible third-party implementations.

**Protocol version:** 1.0.0 (see [VERSIONING.md](VERSIONING.md))
**Canonicalisation profile:** `ACTENON-JCS-STRICT-1` (see [canonicalisation/ACTENON-JCS-STRICT-1.md](canonicalisation/ACTENON-JCS-STRICT-1.md))
**Licence:** Apache-2.0 (see [LICENSE](LICENSE))

---

## What this repository IS

`actenon-protocol` is the **wire contract** for consequential-action execution. It defines the artefacts that cross the trust boundary between an authority broker (such as `actenon-permit`) and a protected resource (verified by `actenon-kernel` or any compatible verifier).

It owns:

* Protocol versioning
* Identifier formats and prefixes
* Execution modes (`brokered`, `resource_owned`)
* Proof claim names
* Refusal codes
* Verification outcome codes
* Execution outcome codes
* Canonicalisation profile identifiers
* `ExecutionProof`
* `ExecutionReceipt`
* `ExecutionRefusal`
* Trusted issuer metadata
* Evidence-linkage fields
* Conformance test vectors
* Generated Python types
* Generated TypeScript types
* OpenAPI-compatible schema components

## What this repository is NOT

It is **not** a fifth commercial product. It is the boundary contract.

It does **not** own:

* Policy evaluation
* Approvals
* Budgets
* Tenant models
* Credential storage
* Provider adapters
* Cloud persistence
* Billing
* The complete hosted `AuthorisedExecutionIntent` lifecycle
* Action execution

Those concerns belong to `actenon-permit`, `actenon-cloud`, `actenon-kernel`'s execution adapters, or the resource owner. The protocol repo defines what crosses the boundary; it does not define what happens on either side of it.

---

## Trust boundary model

```
        ┌─────────────────────┐         ┌─────────────────────────┐
        │  Authority broker   │         │  Protected resource     │
        │  (e.g. Permit)      │         │  (resource-owned        │
        │                     │         │   verifier, e.g. Kernel)│
        │  Issues:            │         │                         │
        │   - authority       │         │  Verifies:              │
        │   - scoped grants   │         │   - ExecutionProof      │
        │  Produces:          │         │     (not the intent)    │
        │   - ExecutionProof  │ ───────▶│                         │
        │     (cryptographic  │  proof  │  Executes if valid;     │
        │      bound to one   │         │  refuses if not.        │
        │      exact action)  │         │                         │
        └─────────────────────┘         │  Emits:                 │
                                        │   - ExecutionReceipt    │
                                        │   - ExecutionRefusal    │
                                        └─────────────────────────┘
```

The boundary artefact is `ExecutionProof`. It is **not** the developer-facing `AuthorisedExecutionIntent`. The intent is the claim; the proof is what gets verified.

---

## Execution modes

The protocol defines two execution modes. The mode is an explicit field on every receipt, refusal, and SDK result model. It is **never** inferred from deployment location.

| Mode | Semantics |
|---|---|
| `brokered` | The deployment obtains or resolves a scoped provider credential, verifies the exact-action proof, and invokes the protected provider or action adapter. The broker holds the credential; the resource trusts the broker's verification. |
| `resource_owned` | The protected resource independently receives a request and proof, verifies it using its own Kernel deployment or compatible verifier, and decides whether to execute. The resource does not trust any broker's assertion; it verifies the proof itself. |

See [protocol/03-execution-modes.md](protocol/03-execution-modes.md) for the full semantics.

---

## Refusal taxonomy

The protocol defines 20 canonical refusal codes, organised into a two-layer disclosure model:

* **Public-safe codes** (`disclosed_code`) — always safe to return to untrusted callers.
* **Detailed codes** (`internal_code`) — only emitted when the disclosure policy permits (trusted callers, internal logs).

See [protocol/07-refusal.md](protocol/07-refusal.md) and [refusals/catalogue.v1.yaml](refusals/catalogue.v1.yaml).

---

## Repository layout

```
actenon-protocol/
├── README.md                      ← you are here
├── LICENSE                        ← Apache-2.0
├── SECURITY.md
├── GOVERNANCE.md
├── VERSIONING.md
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── pyproject.toml                 ← Python types + conformance runner
├── package.json                   ← TypeScript types
├── Makefile
├── protocol/                      ← human-readable specifications (Markdown)
├── schemas/                       ← JSON Schemas (source of truth for wire format)
├── refusals/                      ← machine-readable refusal-code catalogue
├── identifiers/                   ← machine-readable identifier-prefix registry
├── canonicalisation/              ← ACTENON-JCS-STRICT-1 profile specification
├── conformance/                   ← test vectors + Python conformance suite
├── python/                        ← generation-ready Python types (pydantic)
├── typescript/                    ← generation-ready TypeScript types
└── openapi/                       ← OpenAPI 3.1 components
```

---

## Quick start

### Python (conformance runner + types)

```bash
python -m pip install -e ".[dev]"
python -m pytest conformance/python/ -v
```

### TypeScript (types only)

```bash
cd typescript
bun install
bun run typecheck
```

### Validate a fixture against the schemas

```bash
python -m actenon_protocol.validate schemas/execution_proof.v1.json \
    conformance/vectors/proof/valid/minimal_brokered.v1.json
```

---

## Compatibility with existing Actenon repos

This protocol is designed to be wire-compatible with the existing `actenon-kernel`, `actenon-permit`, `actenon-cloud`, and `actenon-scan` repositories at the audited commits (see `CHANGELOG.md` for the audit baseline).

Specifically:

* **Canonicalisation profile:** `ACTENON-JCS-STRICT-1` is the canonical label. The legacy `RFC8785-JCS` label (used by historical proofs in Kernel) is accepted but deprecated. The doc-only label `actenon-jcs-sha256-v1` (which no implementation accepts) is removed.
* **Refusal codes:** The 16 existing `FailureCode` enum members in `actenon-kernel/actenon/outcomes.py` are preserved as aliases. The 20-code catalogue in this repo extends (does not replace) the existing taxonomy.
* **Identifier prefixes:** Existing prefixes (`grant_`, `act_`, `intent_`, `req_`, `ed25519-`) are preserved. New prefixes (`proof_`, `rcpt_`, `rful_`, `exec_`, `authz_`) are added for artefacts that did not previously have a canonical prefix.

See [CHANGELOG.md](CHANGELOG.md) for the full compatibility matrix.

---

## Governance

See [GOVERNANCE.md](GOVERNANCE.md). In summary:

* The protocol is governed by a **protocol maintainer team**, not by any single implementation.
* Breaking changes require a major version bump and a 90-day deprecation period.
* Security fixes are backported to the previous major version for 60 days.

## Reporting a vulnerability

See [SECURITY.md](SECURITY.md). Do not open public issues for security vulnerabilities.

---

## Licence

Apache-2.0. See [LICENSE](LICENSE).
