# 03 — Execution Modes

The protocol defines two execution modes. The mode is an explicit field on every `ExecutionProof`, `ExecutionReceipt`, `ExecutionRefusal`, and SDK result model. It is **never** inferred from deployment location.

## Why modes exist

The audit (findings P-01, C-04) found that the absence of an explicit mode allowed the trust boundary to collapse: Permit's bearer token was treated as a boundary control in some paths, even though the agent never held a Kernel-verifiable proof. Making the mode explicit forces every deployment to declare which trust model is in effect, and prevents the boundary from being collapsed silently.

## Mode: `brokered`

In `brokered` mode, the deployment obtains or resolves a scoped provider credential, verifies the exact-action proof, and invokes the protected provider or action adapter.

```
        ┌──────────────────────┐
        │  Developer agent     │
        │  (no proof in hand;  │
        │   has a broker       │
        │   session)           │
        └──────────┬───────────┘
                   │ 1. requests action
                   ▼
        ┌──────────────────────┐         ┌─────────────────────┐
        │  Broker (e.g.        │         │  Authority broker   │
        │  actenon-cloud       │────2.──▶│  (e.g. permit)      │
        │  gateway)            │  issue  │                     │
        │                      │◀─proof─│  Verifies policy,   │
        │  3. verifies proof   │  3.     │  mints ExecutionProof │
        │     locally          │         │  bound to (action,   │
        │  4. resolves scoped  │         │  target, parameters) │
        │     provider         │         └─────────────────────┘
        │     credential       │
        │  5. invokes provider │
        │     with proof +     │
        │     credential       │
        └──────────┬───────────┘
                   │ 6. provider executes
                   ▼
        ┌──────────────────────┐
        │  Protected provider  │
        │  (e.g. Stripe API)   │
        └──────────────────────┘
```

Characteristics:

* The **broker** holds the provider credential. The agent never sees it.
* The **broker** verifies the proof. The provider trusts the broker's verification (the credential is scoped to the broker, not to per-request verification).
* The **proof** is bound to the exact action. If the broker attempts a different action with the same credential, that is a broker-side policy violation (out of scope for the protocol — the protocol only ensures the proof matches the action).
* **Receipt issuance:** the broker issues the receipt after provider response.

Suitable for: deployments where the broker is the trust hub (e.g. actenon-cloud managed control plane, or a self-hosted actenon-permit gateway).

## Mode: `resource_owned`

In `resource_owned` mode, the protected resource independently receives a request and proof, verifies it using its own Kernel deployment or compatible verifier, and decides whether to execute.

```
        ┌──────────────────────┐
        │  Developer agent     │
        │  (holds the proof;   │
        │   obtained from      │
        │   authority broker)  │
        └──────────┬───────────┘
                   │ 1. request + proof
                   ▼
        ┌──────────────────────────────┐
        │  Protected resource          │
        │  (own Kernel deployment)     │
        │                              │
        │  2. verifies proof locally:  │
        │     - signature              │
        │     - action_hash            │
        │     - audience               │
        │     - expiry                 │
        │     - replay                 │
        │     - issuer trust           │
        │                              │
        │  3. executes action          │
        │     (using its own           │
        │      credentials)            │
        │                              │
        │  4. issues receipt           │
        └──────────────────────────────┘
```

Characteristics:

* The **resource** holds its own credentials. The agent and broker do not have access.
* The **resource** verifies the proof independently. It does not trust the broker's assertion that the proof is valid.
* The **proof** is bound to the exact action. The resource refuses any deviation.
* **Receipt issuance:** the resource issues the receipt after execution.

Suitable for: high-assurance deployments where the resource owner does not want to trust any external broker (e.g. a payment provider that requires its own verification, an IAM control plane that requires its own proof verification, a clinical EHR agent that requires its own verification).

## Mode is explicit, never inferred

The `execution_mode` field MUST be carried on:

1. `ExecutionProof.execution_mode` — set by the issuer at mint time.
2. `ExecutionReceipt.execution_mode` — set by the resource or broker at receipt issuance; MUST match the proof's mode.
3. `ExecutionRefusal.execution_mode` — set by the verifier or resource at refusal issuance.
4. SDK result models (Python `ExecutionResult.execution_mode`, TypeScript `ExecutionResult.execution_mode`).

A verifier MUST refuse a proof whose `execution_mode` it does not support. For example, a broker that only supports `brokered` mode MUST refuse a proof minted with `execution_mode: "resource_owned"` (refusal: `PROOF_INVALID` under public disclosure, `AUDIENCE_MISMATCH` under trusted disclosure — the audience does not match the broker's verification role).

A consumer MUST NOT infer the mode from deployment location. A Cloud-managed gateway could be running in `resource_owned` mode (if the resource owner has configured their own Kernel deployment behind the gateway). A standalone Kernel deployment could be running in `brokered` mode (if it is the broker's verifier). The mode is declared on the artefact, full stop.

## Mode transition

A proof minted under one mode CANNOT be "upgraded" to the other mode. If a deployment needs to switch modes, it must obtain a new proof minted under the new mode. This prevents a `brokered` proof from being presented to a `resource_owned` verifier as if it were a `resource_owned` proof (which would bypass the broker's verification role).

## Conformance

The conformance suite includes fixtures that prove:

* A `brokered` proof is accepted by a `brokered` verifier.
* A `resource_owned` proof is accepted by a `resource_owned` verifier.
* A `brokered` proof is REFUSED by a `resource_owned` verifier (and vice versa) with `PROOF_INVALID` (public) / `AUDIENCE_MISMATCH` (trusted).

See [`conformance/vectors/execution-mode/`](../conformance/vectors/execution-mode/).
