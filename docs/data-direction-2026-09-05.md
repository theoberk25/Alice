# Data direction update — 2026-09-05

Source reviewed: the ten newest turns of
[Zero Trust Hackathon Ideas](chatgpt-conversation://6a960ff3-5770-83ea-8b0d-e77cb11e37da),
following Jared's request to incorporate its changes. This note distinguishes
Jared's described setup from examples and implementation suggestions made by the
other assistant. It supplements the existing PRD without changing tested cyber
schema meanings.

## Updated direction

The latest plan describes one removable USB drive with three directories:

```text
DCAMR_USB/
  policy/
  normal_behavior/
  audit_logs/
```

Policy and normal behavior are inputs. Audit logs are outputs created by DCAMR.
User/agent permissions can be part of the policy input; permission remains
independent of whether an agent or action appears in normal history. The exact
JSON/CSV filenames and root manifest in the referenced answer are examples, not
agreed schemas or existing data files.

The network connects a DCAMR Pi, Technician Mac, Agent Mac and protected motor
controller through an internal switch. The router provides cloud connectivity.
The user first described a second motor-controlling Pi and later mentioned an
ESP in the shopping plan; the controller's final hardware is not resolved here.
The DCAMR device remains the confirmed Pi 4 with 2 GB RAM. Earlier assistant
suggestions of a Pi 5, a larger RAM configuration or dual network interfaces do
not replace that confirmed constraint.

Both local and cloud agents propose actions to DCAMR. DCAMR remains responsible
for authorization before forwarding an approved command to the protected
controller. Cloud SIEM/EDR supply evidence and context. Network placement alone
does not enforce this boundary: the future controller interface must authenticate
DCAMR commands, bind each to the approved request and prevent replay/bypass.

Disconnecting the router uplink is the intended DDIL demonstration. The internal
decision, technician and controller paths need to remain locally usable. Their
addressing, credentials and discovery must work without the cloud; transport and
hardware configuration are still future integration work.

## What the new data requires

| Boundary | Existing cyber slice | Motor/USB follow-up |
| --- | --- | --- |
| Requested action | Five cyber actions with fixed parameter semantics | Define motor operation, degrees/units, target, absolute-versus-relative meaning and retry semantics. |
| Normal behavior | Diagnostic frequencies, known endpoints and transition counts | Normal positions or movements, action rate/sequences, operating context and available device measurements. |
| Local telemetry | Trusted proposal and execution history | Device identity, observation time, freshness/availability, position/state and measurement source where supported. |
| Policy | Still a skeleton | Agent/mission permissions and hard motor limits must be supplied as authority, separately from learned norms. |
| Package input | Validated baseline bytes supplied by a trusted caller | Discover and validate the two input directories, their signed manifests and compatible versions. |
| Audit output | Still a skeleton | Bounded append workflow, persistence failure reporting and history preservation when USB is removed. |
| Model | Synthetic Web-01 lab candidate | A separately versioned motor feature profile and model/reference binding, after command/data semantics are agreed. |

Do not add motor fields to `cyber-behavior-v1` or silently place servo data into its
11 columns. Keep the existing cyber fixtures as regression coverage. The normal
operations directory can eventually supply the relevant profile, but changing
the medium/path does not change the baseline payload's digest or trust semantics.

The input directories should be treated as immutable active inputs by the
decision worker. The writer of package updates remains an unresolved maintenance
role. Directory names or a "read-only" label do not establish filesystem
permissions, signature validation or rollback protection. The USB audit directory
is outside the signed input-package hash set; appending an audit record must not
invalidate policy/baseline signatures.

For the upcoming audit design, distinguish a controller's command receipt or
last commanded position from an independently measured position. A success
response alone must not manufacture sensor confirmation. If physical feedback
is unavailable, report that absence. Hash chaining makes alteration detectable
relative to a trusted checkpoint; it does not itself prevent deletion of the
entire USB log. Local durable retention/checkpoint behavior on USB loss remains
to be decided before implementing the audit writer.

## Decisions to resolve before motor implementation

- Motor-first demo with Web-01 retained as regression coverage, or both domains
  in the initial demo. A specific question is pending with Jared.
- Absolute target angle versus relative movement. A specific question is pending
  because this affects normalization, replay protection and required state.
- Which controller and sensors are actually available, including whether a
  measured position exists. No synthetic sensor values become trusted telemetry.
- Normal movement/position ranges, mission hard bounds and expected action rate.
  Example angles such as 45°, 90° or 135° in the referenced answer are not agreed
  thresholds or hardware capability claims.
- USB removal/reinsertion behavior, audit retention, and the privileged package
  update owner. The previous SD-update-owner question now applies to this USB
  input layout; one USB does not resolve who may modify its trusted inputs.

Jared separately selected trying distinct diagnostic and state-change calibration
references. That experiment remains tracked in the [training guide](anomaly-training.md).
It does not establish a motor calibration profile before the motor's data exists.
