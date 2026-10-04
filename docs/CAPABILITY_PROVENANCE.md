# Capability provenance — pin for dependents

Scan names a power. Permit signs it into a grant and a proof. The Kernel checks that proof before the side effect. Airlock writes the receipt. This package is the shared vocabulary for that path: exact capabilities, `extensions.authority`, and the refusal codes the edge actually emits.

Package **1.5.0**. Wire `PROTOCOL_VERSION` **1.2.0**. Not published to PyPI or npm. Pin the commit named in the protocol pull request (this commit or a descendant on `main`).

```text
actenon-protocol @ git+https://github.com/Actenon/actenon-protocol.git@<commit>
```

Do not stay on PyPI `actenon-protocol` 1.4.0, or on Airlock's previous pin `e988c4d43f8b59d459628a306cd0117109e59d70`, for this contract. 1.4.0 maps `SCOPE_CAPABILITY_MISMATCH` and `SCOPE_MODE_INVALID` to `PARAMETER_MISMATCH`, so a trusted disclosure of an allow-list failure looks like a parameter mismatch. `ExecutionProof` there also has no `extensions` object.

## What changed for callers

- `resolve_alias("SCOPE_CAPABILITY_MISMATCH")` and `resolve_alias("SCOPE_MODE_INVALID")` return those codes. They no longer return `PARAMETER_MISMATCH`.
- Trusted `internal_code` for an edge allow-list failure is `SCOPE_CAPABILITY_MISMATCH`. Public `disclosed_code` is still `PROOF_INVALID`.
- `scope_capabilities_for_mint(())` and any capability containing `*`, `?`, `[`, or `]` raise `CapabilityError`. An empty set is not replaced by the attempted action.
- `scope_capabilities_for_verification(None, capability)` is exactly `(capability,)`. An empty tuple stays empty and authorises nothing.
- `authority_extension(issuer=..., grant_id=...)` is the object Permit signs and `StoreRevocationChecker` reads.
- `unauthenticated_refusal` is `ISSUER_UNTRUSTED` with no trust root and `SIGNATURE_INVALID` when the signature does not verify. Token length is not an input.

Artefacts stamped `1.0.0` and `1.1.0` remain valid. `extensions` is optional.

## Dependent pins

| Repo | What to pin with this protocol | Note |
|---|---|---|
| actenon-permit | `e368dca24af6f316590ce5fd1a0e83a9aebee924` ([#23](https://github.com/Actenon/actenon-permit/pull/23)) | Signs authority only, mints one concrete capability, `StoreRevocationChecker`. |
| actenon-kernel | `fb3a38936f7dade4d25beb91402081eb16c31bfc` ([#43](https://github.com/Actenon/actenon-kernel/pull/43)) | Forged tokens refuse. `ActenonGate(..., capabilities=, revocation_checker=)`. |
| actenon-kernel, when the proof must carry `extensions` | `533c029d63b5ce070a1eb8d8513e8e57a75ec703` | `PCCBMinter.mint` accepts `extensions`. Kernel #43's `mint` does not; Permit checks the signature and skips the extension on a kernel that cannot sign it. |
| actenon-scan | `b7c5951e81acb5c5a84aa11947b76065f47bb452` ([#101](https://github.com/Actenon/actenon-scan/pull/101)) | Names tiktoken downloads, query-only URL hosts, and exports `normalise_path`. |
| actenon-airlock | `d9b1ef11fed698d05fd53a27e674125941b69be6` ([#3](https://github.com/Actenon/actenon-airlock/pull/3)) | Replace the protocol pin with this commit. |

`tests/test_protocol_drift.py` in Kernel and Permit asserts `PROTOCOL_VERSION == "1.1.0"`. Taking this commit means setting that expected wire version to `"1.2.0"`. The Kernel's local `_REFUSAL_CODE_MAP` still maps `SCOPE_CAPABILITY_MISMATCH` to `FailureCode.ACTION_MISMATCH` before the protocol alias lookup, so that map does not have to change for the gate to keep running. Callers of `resolve_alias` / `to_internal_code` do.
