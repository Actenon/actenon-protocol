# Actenon Conformance — the single map

This page is the **canonical entry point** for conformance in the Actenon
ecosystem. If you are implementing an Actenon-compatible component, this
page tells you which conformance suite you must pass and what you can
claim once you pass it.

There are **two conformance suites**. They test different surfaces. Both
are legitimate. Neither subsumes the other.

---

## The two suites at a glance

| | **Protocol conformance** | **Kernel conformance** |
|---|---|---|
| **Lives in** | [`actenon-protocol/conformance/`](conformance/) | [`actenon-kernel/actenon/conformance/`](https://github.com/Actenon/actenon-kernel/tree/main/actenon/conformance) |
| **Tests** | The **wire format** — what every artefact looks like on the wire | The **verifier** — what a valid PCCB is and how it is checked |
| **Vector count** | 129 (83 valid + 46 invalid) | 53 tests in Conformance 1.1.0 (actenon-kernel ≥ 1.3.0) |
| **Categories** | Canonicalisation, proof shape, receipt shape, refusal shape, execution-result shape, execution-mode shape | Canonicalisation strict, verifier SDK (PCCB validation), replay, countersignature, execution state, outcome attestation |
| **Pass mark** | "Actenon-compatible v1.4.0" | "Actenon Verified (Conformance 1.1.0)" |
| **Who needs it** | Anyone implementing the wire format in a new language or framework | Anyone implementing a verifier that decides what a valid PCCB is |
| **Runs on every PR** | Yes ([protocol CI](.github/workflows/ci.yml)) | Yes ([kernel CI](https://github.com/Actenon/actenon-kernel/blob/main/.github/workflows/ci.yml)) |

---

## Which suite do I need to pass?

### If you are implementing the wire format (a new SDK, a new language binding)

You must pass **Protocol conformance** (129 vectors). Your implementation
must accept every valid vector and reject every invalid vector. The
[Runner Specification](conformance/RUNNER_SPEC.md) defines the interface,
and the [standalone runner](conformance/runner.py) is a ready-to-use
Python script you can subclass.

Once you pass, you may claim **"Actenon-compatible v1.4.0"**.

### If you are implementing a verifier (a component that decides what a valid PCCB is)

You must pass **Kernel conformance** (53 tests in Conformance 1.1.0). The kernel's
conformance suite tests the full verifier pipeline: canonicalisation,
PCCB signature verification, replay detection, key lifecycle, and
receipt/refusal emission.

Once you pass, you may claim **"Actenon Verified (Conformance 1.1.0)"**.

### If you are implementing both (a full Actenon stack)

You must pass **both** suites. The Protocol suite proves your wire format
is correct; the Kernel suite proves your verifier is correct. Passing one
does not imply passing the other.

---

## Why two suites?

The Protocol and the Kernel test different things because they are
different layers:

- The **Protocol** is the wire contract. It defines what a proof, receipt,
  refusal, and result *look like* on the wire. An implementation that
  produces and consumes these shapes correctly is Protocol-conformant.
  It does not need to verify signatures — it just needs to canonicalise,
  serialise, and validate the JSON shapes.

- The **Kernel** is the verifier. It defines what a *valid* PCCB is —
  which signatures are acceptable, which key states are trusted, which
  parameters must match, which time windows are valid. An implementation
  that makes correct ALLOW/REFUSE decisions is Kernel-conformant. It must
  also produce and consume the wire format correctly (so it transitively
  depends on Protocol conformance), but it adds the cryptographic
  verification layer on top.

This is the same separation as "JSON Schema validation" (Protocol) vs
"signature verification" (Kernel). Both are necessary; neither is
sufficient alone.

---

## Running the suites

### Protocol conformance

```bash
# In actenon-protocol:
pip install -e ".[dev]"
python conformance/runner.py           # text output
python conformance/runner.py --json    # JSON output for CI
```

### Kernel conformance

```bash
# In actenon-kernel:
pip install -e ".[dev]"
actenon-kernel conformance run         # text output
actenon-kernel conformance run --json  # JSON output for CI
```

---

## Compatibility marks

| Mark | Suite | Version | Meaning |
|---|---|---|---|
| **Actenon-compatible v1.4.0** | Protocol | v1.4.0 | Accepts every valid wire-format vector; rejects every invalid one |
| **Actenon Verified (Conformance 1.1.0)** | Kernel | 1.1.0 | Verifier makes correct ALLOW/REFUSE decisions on every kernel conformance test (53 in 1.1.0), including protocol 13 edge binding |

Both marks are **versioned**. When the wire format changes (Protocol) or
the verifier semantics change (Kernel), the version bumps and
implementations must re-run the suite. Backward compatibility is
guaranteed within a major version.

---

## See also

- [Protocol conformance vectors](conformance/vectors/) — the 129 hash-locked JSON vectors
- [Protocol Runner Specification](conformance/RUNNER_SPEC.md) — the interface external implementations must satisfy
- [Kernel conformance documentation](https://github.com/Actenon/actenon-kernel/blob/main/docs/CONFORMANCE.md) — the verifier suite and its versions
- [VERSIONING.md](VERSIONING.md) — how protocol versioning works
