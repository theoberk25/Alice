# Pi assessment → technician application

This increment implements `dcamr.decision_model.assess_for_technician` and the
`alice-decision-assessment-v1` JSON-compatible output. It calculates behavioral
assessments using the existing scorer and combines them with categorical
permission findings. It does not select a final decision or generate an explanation.
The technician application's local LLM interprets this evidence; **unusual actions
require human technician approval**, as selected by Jared. Transport is another
workstream. The UI may display Approve/Hold/Reject; existing decision wire names
remain ALLOW/HOLD/DENY until the transport owners coordinate a migration.

## Call boundary

```python
from dcamr.decision_model import (
    AssessmentBinding, PermissionFinding, assess_for_technician,
)

packet = assess_for_technician(
    binding,             # AssessmentBinding: trusted coordinator's exact bindings
    permission,          # PermissionFinding: trusted permission resolver output
    observation_bytes,   # existing context-behavior-observation-v1 bytes
    contextual_model,    # existing fitted ContextualModel or compatible scorer
)
```

`AssessmentBinding` carries evaluation ID, request ID, normalized request SHA-256,
observation SHA-256, PRE_ACTION/POST_ACTION phase and execution ID (post only).
The normalized request hash must cover the actual agent, action, target and
parameters using the integration team's agreed serialization. This component does
not introduce a competing action schema or authenticate a supplied hash.

`PermissionFinding` contains that same request digest, outcome, package generation
and digest, matching rule IDs and reason codes. Outcomes are PERMITTED,
PROHIBITED, REVIEW_REQUIRED, UNRESOLVED and NOT_READY. The last two explicitly
represent incomplete resolution or unusable trusted state. Definitive outcomes
require package provenance; every outcome requires a reason. These are typed
in-process inputs, **not permission claims accepted from an agent or LLM**.
The permission resolver, USB verification/activation and live freshness checks
remain unimplemented integrations; this function does not turn synced files into
an authorization grant. Keep permission categorical: there is no invented
permission probability or combined risk number.

The coordinator must authenticate sources and bind actual requested parameters,
operating context and telemetry to the observation. Send the corresponding
normalized request alongside this packet to the technician app so the LLM can
see the action/target/parameters; verify that request against the packet's digest.
Agent prose remains untrusted context and cannot override structured findings.

## Output and interpretation

| Field | Meaning |
| --- | --- |
| `binding` | Original outer IDs/digests, retained even when observation parsing fails. |
| `permission` | Resolver finding and exact package/rule provenance. |
| `anomaly_status`, `anomaly_reason_codes` | Success, skipped, unavailable or invalid/error status, with bounded machine reasons. |
| `anomaly` | Existing full contextual assessment: score, band, raw score, model/profile/calibration identifiers, context, measurement comparisons and sources; null if skipped or the scorer fails validation. |
| `approval_blockers` | Conditions that must be resolved before any approval can execute. An empty list is not an execution grant. |
| `review_signals` | ELEVATED/HIGH anomaly and outside-training-range evidence, retained independently of score. |
| `human_approval_required` | True for PRE_ACTION unusual evidence or explicit permission review; LLM output alone cannot clear it. |
| `decision_owner` | TECHNICIAN_APPLICATION. |
| `decision`, `explanation` | Null: supplied later by the technician application. |
| `execution_authorized` | Always false. This packet is never an execution token. |
| `score_semantics` | NORMAL_TAIL_RANK_NOT_PROBABILITY. |

The existing calibration uses LOW below .95, ELEVATED from .95 to below .99,
and HIGH from .99. These are synthetic-lab thresholds, not deployment acceptance.
They do not replace permissions or establish electrical safety.

- PROHIBITED short-circuits PRE_ACTION scoring, records HARD_PROHIBITION and SKIPPED, and
  cannot be overridden by LLM or technician approval.
- REVIEW_REQUIRED retains its permission blocker even when behavior is normal.
- Missing/unresolved permissions or unavailable anomaly information block
  approval. Human approval alone does not repair missing evidence or trust.
- ELEVATED/HIGH, or a measured value outside the fitted training range even with
  a LOW score, requires human approval before execution.
- POST_ACTION assesses a result already observed. Its review signals remain;
  `human_approval_required` is false because retrospective approval is not an
  execution control. Investigate/escalate findings without rewriting the original
  authorization or triggering an automatic corrective action. An observed prohibited
  execution still receives POST_ACTION scoring, retaining its hard-prohibition flag.

A later enforcement adapter must check exact request/approval binding, human
approval where required, authority, current permissions and durable audit receipt.
This module implements no response ingestion, execution or audit persistence.
The application must enforce structured blockers outside the LLM prompt; prompt
instructions alone cannot enforce a prohibition or human-approval requirement.

## Resource and test boundary

The wrapper uses the standard library and imports no numerical runtime itself.
The supplied fitted contextual scorer still uses NumPy/scikit-learn on the Mac;
this increment does **not** export trees or deploy the model to the Pi. Data-only
forest export and parity checks remain prerequisites for the lightweight Pi path.
Observation bytes are capped at 32 KiB. Scorer deadlines/process isolation and
Pi memory/latency measurements remain runtime work.

Run `python3 -m unittest tests.test_decision_assessment -v`. Tests cover normal,
unusual, range flags, hard-deny short circuit, missing evidence/model, redacted
scorer failures, binding mismatch, pre/post separation and real contextual scoring.
Fixtures are unitless synthetic signals, not accepted ESP measurements.
