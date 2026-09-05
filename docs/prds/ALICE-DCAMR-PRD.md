# ALICE / DCAMR — Product Requirements Document

**Status:** Hackathon MVP planning baseline
**Audience:** Project team, judges, and technical reviewers
**Scope:** A safe, isolated demonstration of a disconnected-capable authorization boundary for autonomous cyber-agent actions.

## 1. Product Summary

ALICE (Authenticated Local Identity & Cyber Enforcement) is the technician-facing companion to DCAMR (Disconnected Cyber Agent Mission Router), a local security harness that evaluates consequential actions proposed by an autonomous cyber agent before those actions reach a protected system.

The central product claim is simple: an agent may be authenticated, authorized to investigate, and still manipulated or mistaken. DCAMR independently evaluates the proposed action against signed policy, behavioral expectations, available evidence, and bounded agent-supplied context. It continues enforcing under disconnected, disrupted, intermittent, or limited (DDIL) conditions.

For the hackathon, the product is a controlled lab demonstration—not a production security platform. All attack-like events, target systems, telemetry, and agent actions are simulated and harmless.

## 2. Problem Statement

Autonomous cyber agents can consume manipulated content, make incorrect inferences, or request actions outside their mission intent. Conventional authentication alone does not prevent an authenticated agent from proposing a harmful action.

DCAMR creates a separate authorization boundary between the agent and protected tools. It must make authoritative machine decisions locally, even when cloud data is unavailable. The workstation may explain those decisions to a technician, but an explanatory LLM must never determine whether an action executes.

## 3. Goals and Success Criteria

### Goals

- Demonstrate a local, independent enforcement decision for each consequential agent action.
- Demonstrate deterministic denial of a prohibited action.
- Demonstrate behavioral/anomaly-informed escalation for an unusual but not prohibited action.
- Demonstrate the structured `REQUEST_CONTEXT` loop and a re-evaluation outcome.
- Demonstrate signed policy or baseline package validation, including rejection of a tampered package.
- Demonstrate continued decision-making during a simulated DDIL condition.
- Give a technician a clear dashboard view of the raw decision, its provenance, and available review actions.

### Hackathon success criteria

The end-to-end demo succeeds when a reviewer can observe the following sequence:

1. Normal diagnostic actions receive `ALLOW`.
2. A prohibited request such as `disable_edr(Web-01)` receives `DENY` from deterministic policy.
3. A novel outbound request receives `REQUEST_CONTEXT`; a bounded structured response is accepted and re-scored.
4. Insufficient or unverified evidence plus a high anomaly result produces `HOLD`.
5. A tampered signed package is rejected.
6. The dashboard and local decision flow remain available after simulated cloud disconnection.
7. A technician can inspect the raw decision record and its sources before taking a demo review action.

## 4. Users and Trust Boundaries

| Actor or component | Role | Trust boundary |
| --- | --- | --- |
| Autonomous cyber agent | Requests actions and submits bounded context/evidence | Untrusted for authorization; cannot bypass or change DCAMR policy/baselines |
| DCAMR on Raspberry Pi | Makes and records the authoritative decision | Local enforcement authority |
| Signed policy and baseline packages | Define mission rules and normal operating behavior | Externally governed, read-only authority |
| Technician workstation | Explains and displays the decision; provides review controls | May not override a deterministic denial or alter raw records |
| Local LLM | Produces a human-readable explanation | Never authorizes, denies, or rewrites a decision |
| Cloud SIEM/EDR | Provides enrichment and later evidence verification | Optional; never a requirement for local enforcement |

## 5. MVP Functional Requirements

### FR-1: Action-request normalization

DCAMR must accept a structured agent action request containing, at minimum, agent identity, mission identifier, action/tool, target, parameters, and referenced evidence. It normalizes this request into a stable internal record for evaluation and logging.

### FR-2: Deterministic policy evaluation

DCAMR must evaluate the normalized request against the active signed Mission Policy Package. It must support allowed, approval-required, and prohibited operations. A prohibited operation must return `DENY` without entering a context or technician-approval path.

### FR-3: Anomaly evaluation

DCAMR must evaluate otherwise-permitted actions against a supplied operational baseline. For the demo, this includes enough features to identify unusual targets, outbound destinations, action sequences, or evidence conditions. The anomaly contribution must be surfaced in the raw decision record.

### FR-4: Decision fusion and machine outcomes

DCAMR must combine policy, anomaly, evidence, and available context into exactly four machine outcomes:

- `ALLOW`
- `REQUEST_CONTEXT`
- `HOLD`
- `DENY`

Hard policy always takes precedence over anomaly, evidence, or agent context.

### FR-5: Structured context-request loop

For novel or insufficiently justified actions that are not prohibited, DCAMR must request bounded, schema-defined context. It must accept only the defined fields, record each attempt, re-evaluate after a response, and stop after a small fixed number of attempts by returning `HOLD`.

### FR-6: Evidence status

DCAMR must record the status of evidence references as locally verified, unavailable under DDIL, missing, or otherwise not verified. The demo must make it clear that evidence status affects risk and review, but cannot override a deterministic prohibition.

### FR-7: Signed-package verification

DCAMR must load the Mission Policy Package and Operational Baseline Package as distinct signed inputs. It must display package identity/version/status and reject a package that fails integrity or signature verification.

### FR-8: Tamper-evident decision records

Every decision and context exchange must generate a raw record containing outcome, policy result, anomaly result, evidence status, context attempts, timestamps, and provenance/source references. A later reconciliation must append to the record rather than alter the original decision.

### FR-9: Technician dashboard and raw-decision view

The dashboard must display the decision state, key rationale, provenance, package status, evidence status, and recent activity. It must provide a raw-decision view distinct from the LLM explanation. The dashboard may expose technician actions such as `APPROVE ONCE`, `REJECT`, `INVESTIGATE`, and `HOLD` only for actions already held for review.

### FR-10: Technician identity check for demo approval

For the demo’s consequential approval path, ALICE facial verification must gate `APPROVE ONCE`. Passing verification authorizes only the exact held request once; failing verification blocks approval.

### FR-11: DDIL and reconciliation demonstration

When cloud connectivity is simulated as unavailable, local policy, baseline, decisioning, dashboard, and audit logging must continue to operate. When connectivity returns, externally verifiable evidence may be reconciled and appended to the original record without revising its original outcome.

## 6. Demo Flow

1. Show healthy-environment diagnostic requests and `ALLOW` outcomes.
2. Introduce safe, simulated suspicious telemetry in the isolated lab.
3. Show an agent request influenced by manipulated content: `disable_edr(Web-01)`.
4. Show deterministic `DENY` and the corresponding policy provenance.
5. Show an unusual `allow_outbound` request, `REQUEST_CONTEXT`, structured agent response, and re-score to `HOLD`.
6. Show the technician dashboard, raw-decision record, and local explanation side by side.
7. Insert or select a tampered package and show validation failure/rejection.
8. Simulate DDIL; show that decisions and dashboard updates continue.
9. Restore connectivity and show appended evidence reconciliation.

## 7. Repository and Branching Plan

The repository should make the security boundary and team workstreams legible without prematurely locking implementation choices.

```text
docs/                 PRD, architecture, demo script, research
dcamr/                Pi-side decision runtime and local API
  policy/             policy-package loading and evaluation
  anomaly/            feature preparation and anomaly-model interface
  decision/           normalization, fusion, context loop, audit records
  packages/           package verification and package readers
workstation/          dashboard, raw-decision view, local explanation, approval flow
hardware/             Raspberry Pi, readers, camera, setup and runbook materials
ml/                   anomaly model assets, interface contract, evaluation notes
demo/                 synthetic scenarios, fixtures, orchestration, presentation assets
shared/               versioned request/response schemas and test fixtures
tests/                end-to-end and component-level test coverage
```

Use short-lived branches from `dev` with the `codex/` prefix unless the team agrees otherwise. Each branch should cover one coherent, reviewable change; integration work occurs through pull requests into `dev`. Suggested patterns are `codex/dashboard-*`, `codex/ml-*`, `codex/hardware-*`, `codex/dcamr-*`, and `codex/demo-*`. The PRD does not require a branch-per-person or prescribe a rigid commit workflow.

## 8. Team Work Boundaries

Assignments below reflect only responsibilities the team has already named. They are intended as coordination boundaries, not exhaustive task lists.

| Team member | Primary responsibility | Collaboration boundary |
| --- | --- | --- |
| Alex | Technician dashboard and end-of-stream work | Consumes shared raw-decision schemas; coordinates dashboard/demo presentation needs |
| Theo | Overall architecture, design, and project work | Co-owns cross-component decisions and the demo with Merek |
| Merek | Overall architecture, design, and project work | Co-owns cross-component decisions and the demo with Theo |
| Jared | ML/anomaly-model portion integrated into the anomaly path | Exposes a stable anomaly-result interface for DCAMR fusion and dashboard provenance |
| Xavier | Raspberry Pi and hardware portions | Owns physical setup/integration constraints, readers, camera, and hardware runbook |
| Entire team | Demo | Merek and Theo provide particular emphasis on the narrative and integration flow |

## 9. Cross-Component Interface Expectations

To keep parallel work compatible, the team should agree on a versioned shared request and raw-decision schema before component work becomes deeply coupled. At minimum, the shared decision record should contain:

- request identifier, timestamp, agent, mission, action, target, and parameters;
- policy result and policy-source reference;
- anomaly score/result and baseline-source reference;
- evidence items and verification status;
- context-request status and attempt count;
- final machine outcome and risk/reason codes;
- package versions/status; and
- technician action and verification result when applicable.

The Pi’s raw decision is authoritative. The dashboard and local LLM consume that record; they do not redefine it.

## 10. Non-Functional Requirements

- **Safety:** All demo actions must remain inside isolated, synthetic, harmless lab resources.
- **Explainability:** A judge or technician must be able to identify why a decision occurred and what source produced each key factor.
- **Offline resilience:** No cloud dependency may be required for the core local decision path.
- **Integrity:** Policy and baseline inputs must be distinguishable, versioned, and integrity-checked for the demo.
- **Auditability:** Original decisions must be preserved; reconciliation only appends later findings.
- **Demo reliability:** The scripted demo should have deterministic fixtures or fallbacks so it does not depend on live enterprise services.

## 11. Acknowledged Limitations and Explicitly Out of Scope

These are intentionally excluded from the hackathon MVP but should be acknowledged in the demo and repository documentation.

| Item | MVP boundary | Intended future direction |
| --- | --- | --- |
| Enterprise SIEM/EDR integrations | Use simulated/local cached evidence rather than live enterprise connectors | Production connectors, credential management, sync, and reconciliation workflows |
| Production policy lifecycle | Demonstrate fixed signed packages and tamper rejection | Issuance, key rotation, revocation, approval workflow, and enterprise policy governance |
| Full anomaly-model training lifecycle | Integrate a bounded anomaly result for demo behavior | Data pipelines, calibration, retraining governance, drift monitoring, and evaluation datasets |
| Production enforcement integrations | Protect demo systems and simulated agent tools only | Integrations with real EDR, firewall, server, and application control planes |
| Cryptographic and hardware hardening | Demonstrate integrity properties at hackathon depth | Secure boot, hardware-backed keys, hardened storage, supply-chain controls, and penetration testing |
| LLM safety and evaluation | Use the workstation LLM only as a non-authoritative explainer | Prompt-injection evaluation, observability, model governance, and formal explanation-quality testing |
| Facial verification robustness | Demonstrate a local approval gate | Enrollment lifecycle, anti-spoofing/liveness detection, privacy controls, and biometric compliance |
| High availability and scale | Single-node demo setup | Redundancy, fleet management, load testing, monitoring, and operational support |
| Full user/role administration | Use demo identities and roles | Enterprise identity, RBAC, delegated administration, and audit controls |

## 12. Acceptance Checklist

Before the demo, verify that the team can show each of these without relying on an unplanned live dependency:

- [ ] Normal allowed action produces an auditable `ALLOW`.
- [ ] Prohibited action produces an auditable `DENY` without a context path.
- [ ] Novel permitted action produces `REQUEST_CONTEXT` and supports one structured re-evaluation.
- [ ] High-risk/insufficient-evidence action produces `HOLD`.
- [ ] Dashboard shows decision provenance and raw record.
- [ ] Tampered package is rejected.
- [ ] DDIL simulation preserves local decisioning and dashboard visibility.
- [ ] Reconnection appends a reconciliation result without rewriting history.
- [ ] `APPROVE ONCE` is scoped to one held action and gated by the demo identity check.
