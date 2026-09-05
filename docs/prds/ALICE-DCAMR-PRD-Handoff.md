# ALICE / DCAMR — Developer PRD Handoff Package

**Parent PRD:** [`ALICE-DCAMR-PRD.md`](./ALICE-DCAMR-PRD.md)
**Purpose:** Give each workstream enough shared context to write a focused implementation PRD without redefining the product boundary.

## 1. How to Use This Package

The parent PRD is the source of truth for product scope, decision authority, demo expectations, trust boundaries, and acknowledged limitations. A child PRD narrows that scope to one workstream and must not conflict with it.

Each developer receives:

1. The parent PRD.
2. This handoff package.
3. The architecture document and relevant demo scenario.
4. The child-PRD template in Section 5.

Each child PRD should state its deliverable, acceptance criteria, files/folders it owns, the shared contracts it consumes or produces, local test evidence, and the branch scope. It should avoid assigning work outside its workstream.

## 2. Proposed Child PRDs

| Child PRD | Primary owner(s) | Scope boundary | Key dependency |
| --- | --- | --- | --- |
| Dashboard and end-of-stream experience | Alex | Technician dashboard, raw-decision display, explanation display, and end-of-stream presentation | Consumes the versioned raw-decision schema; does not determine machine outcomes |
| Anomaly-model integration | Jared | Demo anomaly model, feature/result contract, and anomaly provenance | Produces a stable anomaly-result payload for decision fusion |
| Pi and hardware integration | Xavier | Raspberry Pi setup, package readers, camera/face-verification hardware path, and runbook | Consumes local service/schema contracts; does not define security policy semantics |
| Core DCAMR integration and demo | Merek and Theo | Shared architecture/design decisions, decision runtime integration, shared schemas, and demo orchestration | Owns cross-workstream compatibility and the integrated demo narrative |

The whole team participates in the demo. Merek and Theo provide added focus on integration and narrative, as defined in the parent PRD.

## 3. Shared Contract: Raw Decision Record

Before workstreams become deeply coupled, agree on a versioned raw-decision record. The Pi-side decision runtime is authoritative; all other consumers render or augment this record without changing the recorded machine outcome.

```json
{
  "schema_version": "1.0",
  "request_id": "req-demo-001",
  "timestamp": "2026-09-05T14:07:31Z",
  "request": {
    "agent_id": "diagnostic-agent-04",
    "mission_id": "INC-291",
    "action": "allow_outbound",
    "target": "Web-01",
    "parameters": { "destination": "unknown-host" }
  },
  "policy": {
    "result": "REVIEW",
    "rule_id": "P-12",
    "source": "POLICY_USB:/airbase/p12.rego"
  },
  "anomaly": {
    "result": "HIGH",
    "score": 0.74,
    "source": "OPS_BASELINE:/web01/network.json"
  },
  "evidence": [
    { "id": "EDR-9921", "status": "LOCALLY_PRESENT" }
  ],
  "context": {
    "status": "REQUESTED",
    "attempt_count": 1
  },
  "packages": {
    "policy": { "id": "mission-policy", "version": "18", "status": "VALID" },
    "baseline": { "id": "ops-baseline", "version": "42", "status": "VALID" }
  },
  "decision": {
    "outcome": "HOLD",
    "risk": 0.78,
    "reason_codes": ["DESTINATION_NOVELTY", "INSUFFICIENT_EVIDENCE"]
  },
  "technician_review": null,
  "reconciliation": []
}
```

### Contract rules

- `decision.outcome` is one of `ALLOW`, `REQUEST_CONTEXT`, `HOLD`, or `DENY`.
- A deterministic policy `DENY` is final; neither anomaly results, context, the dashboard, nor the LLM may replace it.
- The local LLM can add a display-only explanation. It must not modify this record.
- `reconciliation` only appends new evidence findings after connectivity returns; it never replaces the original decision.
- Dashboard fixtures and ML fixtures should use this schema so parallel work can run before all components are integrated.

## 4. Repository and Branch Handoff

The parent PRD proposes these top-level boundaries:

```text
dcamr/       Pi-side runtime, policy, anomaly interface, decision fusion, packages, audit
workstation/ dashboard, raw-decision view, explanation, technician approval path
hardware/    Pi, readers, camera, setup instructions, runbook
ml/          anomaly model assets, evaluation notes, integration contract
demo/        synthetic scenarios, fixtures, orchestration, presentation materials
shared/      versioned schemas and shared test fixtures
tests/       component and end-to-end tests
docs/        PRDs, architecture, research, demo script
```

Use a short-lived branch per coherent change, based on `dev`, with the `codex/` prefix unless the team explicitly agrees otherwise. Examples:

- `codex/dashboard-decision-view`
- `codex/ml-anomaly-contract`
- `codex/hardware-pi-runbook`
- `codex/dcamr-decision-schema`
- `codex/demo-ddil-scenario`

Branches should not be treated as personal territory. A child PRD identifies folders and shared contracts to coordinate reviews, not to prevent necessary collaboration.

## 5. Child PRD Template

Copy this template into `docs/prds/<workstream>-prd.md` and complete only the sections relevant to the workstream.

```markdown
# [Workstream Name] PRD

**Parent PRD:** `docs/ALICE-DCAMR-PRD.md`
**Owner(s):** [Name(s)]
**Status:** Draft

## 1. Purpose

State the workstream's contribution to the hackathon MVP in two or three sentences.

## 2. In Scope

- [Concrete deliverable]
- [Concrete deliverable]

## 3. Out of Scope and Acknowledged Limitations

- [Deliberately excluded item and its intended future direction]

## 4. Interfaces

### Consumes

- [Shared schema, service, hardware input, or fixture]

### Produces

- [Versioned response, UI, hardware capability, fixture, or runbook]

### Contract Rules

- [Non-negotiable rule from parent PRD, such as “policy DENY is final”]

## 5. Functional Requirements

- **FR-1:** [Observable behavior]
- **FR-2:** [Observable behavior]

## 6. Acceptance Criteria

- [ ] [A reproducible behavior a reviewer can observe]
- [ ] [A reproducible behavior a reviewer can observe]

## 7. Repository and Branch Scope

- **Primary folders:** `[exact/folder]`
- **Tests/fixtures:** `[exact/folder]`
- **Suggested branch prefix:** `codex/[workstream]-`

## 8. Demo Contribution

Describe the exact moment, screen, device behavior, or handoff this workstream supports in the demo.

## 9. Validation

- [Test, fixture replay, hardware check, or manual demo check]
```

## 6. Integration Order

The workstreams may proceed in parallel once the shared schema is accepted. The practical integration order is:

1. Establish the shared request and raw-decision fixtures.
2. Implement or stub the Pi-side decision producer against those fixtures.
3. Let dashboard and ML work consume/produce fixtures through the agreed contract.
4. Connect Pi hardware and workstation paths using the same contract.
5. Run the end-to-end demo scenario and resolve interface mismatches.

This is an integration sequence, not an assignment expansion. Each child PRD remains responsible only for the boundaries in Section 2.
