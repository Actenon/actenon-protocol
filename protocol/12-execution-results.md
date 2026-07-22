# 12 — Execution Results

Every execution attempt — brokered or resource-owned — produces an
`ExecutionResult`. The result model is **discriminated** by `mode`:
the two result shapes are not interchangeable, and consumers MUST NOT
treat one as the other. This document specifies the discriminated
union, the per-mode state machines, the receipt fields, and the
finality rules.

For the trust model behind each mode, see
[`03-execution-modes.md`](03-execution-modes.md). For the JSON Schema
of the result model, see
[`schemas/execution_result.v1.json`](../schemas/execution_result.v1.json).

## 1. Discriminated union

```
ExecutionResult =
  | BrokeredExecutionResult
  | ResourceOwnedExecutionResult
```

The `mode` field is the discriminator. A consumer that receives a
result with `mode: "brokered"` MUST NOT read `resource_receipt_received`
or `submission_reference` — those fields do not exist on
`BrokeredExecutionResult`. The same applies in reverse: a consumer
that receives `mode: "resource_owned"` MUST NOT read
`receipt_verified` (brokered-only field); it must read
`resource_receipt_verified`.

A result with `mode: "brokered"` and a `resource_receipt_received`
field is invalid. A result with `mode: "resource_owned"` and a
`receipt_verified` field is invalid. Schema validation rejects both.

## 2. Brokered states

| State             | Finality   | `provider_execution_observed` | Description                                                       |
|-------------------|------------|-------------------------------|-------------------------------------------------------------------|
| `succeeded`       | final      | true (required)               | Provider returned a success response; the broker observed it.     |
| `failed`          | final      | true (required)               | Provider returned a failure response; the broker observed it.     |
| `refused`         | final      | (any)                         | The broker refused to invoke the provider (proof invalid, action out of scope, credential missing, parameter validation failed). No provider call was attempted. |
| `outcome_unknown` | non_final  | (any)                         | The provider call was attempted but the outcome could not be determined (timeout, partial response, reconciliation pending). |

State transitions:

```
                  ┌───────────────┐
                  │   (initial)   │
                  └───────┬───────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌─────────┐ ┌───────────────┐
        │succeeded │ │ failed  │ │outcome_unknown│
        └──────────┘ └─────────┘ └───────┬───────┘
              │           │             │
              ▼           ▼             ▼
            (final)     (final)    reconcile
                                      │
                          ┌───────────┼───────────┐
                          ▼           ▼           ▼
                    ┌──────────┐ ┌─────────┐ ┌───────────────┐
                    │succeeded │ │ failed  │ │outcome_unknown│
                    └──────────┘ └─────────┘ └───────────────┘
                      (final)     (final)      (still non-final)
```

`refused` is a separate entry point — the broker refuses before any
provider call, so it does not pass through `outcome_unknown`.

**Hard rule:** `succeeded` requires `provider_execution_observed = true`.
A brokered result with `state: "succeeded"` and
`provider_execution_observed: false` is invalid. This is what
prevents a credential-resolution success from being reported as an
execution success.

## 3. Resource-owned states

| State             | Finality   | `provider_execution_observed` | `resource_receipt_received` | `resource_receipt_verified` | Description                                                              |
|-------------------|------------|-------------------------------|-----------------------------|------------------------------|--------------------------------------------------------------------------|
| `submitted`       | non_final  | false (required)              | false (required)            | false                        | The request + proof were submitted to the resource boundary. No ack yet. |
| `accepted`        | non_final  | false (required)              | (any)                       | (any)                        | The resource accepted the request but has not executed yet.              |
| `refused`         | final      | (any)                         | (any)                       | (any)                        | The resource refused the request (proof invalid, action out of scope, resource policy denied). |
| `succeeded`       | final      | true (required)               | true (required)             | true (required)              | The resource executed the action and returned a cryptographically verified receipt. |
| `failed`          | final      | true (required)               | (any)                       | (any)                        | The resource executed the action and it failed.                          |
| `outcome_unknown` | non_final  | (any)                         | (any)                       | (any)                        | The resource returned no receipt or an unverifiable receipt; final state cannot be determined. |

State transitions:

```
                  ┌───────────────┐
                  │   (initial)   │
                  └───────┬───────┘
                          │ submit
                          ▼
                  ┌───────────────┐
                  │   submitted   │ (non-final)
                  └───────┬───────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌─────────┐ ┌───────────────┐
        │ accepted │ │ refused │ │outcome_unknown│
        └────┬─────┘ └─────────┘ └───────────────┘
             │         (final)     (non-final)
             │
             ▼
       ┌─────────────────────────────────┐
       │  resource executes the action   │
       └─────────────┬───────────────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
   ┌──────────┐ ┌─────────┐ ┌───────────────┐
   │succeeded │ │ failed  │ │outcome_unknown│
   └──────────┘ └─────────┘ └───────────────┘
     (final)     (final)      (non-final)
```

**Hard rules:**

* `submitted` and `accepted` are NOT success states. A consumer that
  treats `submitted` as `succeeded` is making a category error.
* `succeeded` requires `resource_receipt_received = true` AND
  `resource_receipt_verified = true`. A resource-owned result with
  `state: "succeeded"` and `resource_receipt_verified: false` is
  invalid. This is what prevents a forged or missing resource receipt
  from being reported as execution success.
* `submitted` requires `provider_execution_observed = false` and
  `resource_receipt_received = false`. This is what prevents
  "submission succeeded" from being conflated with "execution
  succeeded".

## 4. Receipt fields

Every receipt (whether produced by the broker in `brokered` mode or by
the resource in `resource_owned` mode) MUST carry:

| Field                          | Source            | Description                                                                                       |
|--------------------------------|-------------------|---------------------------------------------------------------------------------------------------|
| `execution_mode`               | proof + receipt   | `brokered` or `resource_owned`. MUST match the proof's mode.                                      |
| `verified_by`                  | receipt           | Identifier of the component that verified the proof.                                              |
| `executed_by`                  | receipt           | Identifier of the component that invoked the provider (brokered) or executed the action (resource). |
| `provider_execution_observed`  | receipt           | True if the executor observed the provider's response.                                            |
| `resource_receipt_received`    | receipt (resource_owned only) | True if the resource returned a receipt.                                              |
| `resource_receipt_verified`    | receipt (resource_owned only) | True if the resource receipt's signature verified.                                    |
| `finality`                     | receipt           | `final` or `non_final`. Derived from the state per the tables above.                              |

A receipt that omits `execution_mode` is invalid. A receipt with
`execution_mode: "resource_owned"` that omits
`resource_receipt_received` is invalid. These are not optional
fields; they are the boundary itself.

## 5. Forged and missing receipts

A `resource_owned` flow that submits a request and receives NO
resource receipt MUST remain in `submitted` (or `outcome_unknown` if
the submission itself timed out). It MUST NOT transition to
`succeeded` on the basis of "submission succeeded".

A `resource_owned` flow that receives a resource receipt whose
signature does NOT verify against the resource's published signing
key MUST transition to `outcome_unknown` (or `refused` if the
resource explicitly refused). It MUST NOT transition to `succeeded`.
This is the cryptographic boundary: a forged receipt cannot elevate
the state.

## 6. Mode immutability

A proof minted under one mode CANNOT be "upgraded" to the other
mode. A receipt minted under one mode CANNOT be re-interpreted under
the other mode. This is enforced at the schema level: the `mode`
field is `const` within each branch of the discriminated union, so a
brokered receipt cannot be re-serialised as a resource-owned receipt
without violating the schema.

## 7. Conformance

The conformance suite includes fixtures that prove:

* A `BrokeredExecutionResult` with `state: "succeeded"` and
  `provider_execution_observed: false` is rejected by schema
  validation.
* A `ResourceOwnedExecutionResult` with `state: "succeeded"` and
  `resource_receipt_verified: false` is rejected by schema
  validation.
* A `ResourceOwnedExecutionResult` with `state: "submitted"` and
  `finality: "final"` is rejected by schema validation.
* A result that mixes brokered-only and resource-owned-only fields is
  rejected by schema validation.

See [`conformance/vectors/execution-result/`](../conformance/vectors/execution-result/).
