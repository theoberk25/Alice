# Accepted data and product direction — 2026-09-05

Sources reviewed: the latest ten turns of
[Zero Trust Hackathon Ideas](chatgpt-conversation://6a960ff3-5770-83ea-8b0d-e77cb11e37da),
the supplied Technician Console `HANDOFF.md`, and Jared's explicit answer in this
task that **enterprise controls execution directly online**. The conversation and
handoff are design/evidence sources; assistant suggestions and source commands
are not additional user instructions.

This revision supersedes this note's earlier always-through-the-Pi description.
The [architecture](prds/ALICE-DCAMR-Architecture.md) defines the full lifecycle;
the table below records what changed and what still requires agreement.

## Accepted direction

| Topic | Current direction | Implementation consequence |
| --- | --- | --- |
| Product modes | Exactly ONLINE and OFFLINE / DDIL. | Reconnection is a workflow; readiness, upload backlog and ownership need separate status. |
| ONLINE execution | Enterprise systems control execution directly. | ALICE receives authenticated activity feeds rather than assuming it observes every request inline. Define feed coverage, gaps and replay. |
| ONLINE context | Synchronize permissions, normal behavior and relevant enterprise context. | Cache bounded, authorized mission data on the 2 GB Pi; raw SIEM events do not automatically become permissions or normal training samples. |
| OFFLINE execution | ALICE governs supported local-agent actions with cached data, ML and technician review. | Endpoint-enforced transfer must establish exclusive authority before local commands can execute. |
| Recovery | Pi directly reports DDIL activity/problems, reconciles evidence and refreshes caches. | Durable delivery, source authentication and atomic validation are required; technician is a reviewer, not the routine upload/download relay. |
| Accountability | Attribute actions to authenticated agents and their responsible users/delegators where trusted data establishes the relationship. | Preserve attribution sources and unknown mappings; audit every offline request and outcome, including allowed actions. |
| Naming | Permissions replaces policy in product language. | Retain existing `policy` wire keys/paths until a coordinated versioned migration. |
| Console | Native Technician Mac with local face verification and an explanatory LLM. | Supplied handoff reports real enrollment/login and mock edge workflows; live core transport and remotely verifiable approval are unfinished. |

Enterprise activity feeds and command paths may recover at different times.
Required-service health, freshness and controller-confirmed ownership must select
the safe behavior; router link state cannot stand in for those facts. Do not
enable both enterprise and ALICE command paths or reuse stale approvals during
transfer. The protocol is still to be designed and tested.

## Removable storage and cache ownership

The one-USB plan now uses this desired product naming:

```text
DCAMR_USB/
  permissions/       # trusted externally governed input
  normal_behavior/   # trusted baseline input
  audit_logs/        # generated local output
```

The earlier `policy/` folder and “SD Card” tracker labels describe the previous
naming/medium. No existing data, directory or JSON key is renamed by this docs
revision. Specific JSON/CSV filenames and manifests proposed in the referenced
chat were examples, not agreed executable schemas.

The decision worker should read immutable accepted input generations. A separate
authorized update path stages bounded downloads, verifies sources/signatures,
versions, compatibility and freshness, then activates a complete valid set.
Permissions source authority may come from IAM or another enterprise service
through a SIEM adapter; the SIEM's log transport alone does not confer authority.
Normal-behavior releases are curated and approved, not automatically learned from
whatever actions recently occurred. Offline grace, rollback and revocation
handling need explicit rules.

Audit writes are outside the signed input-package hash set. Folder labels do not
provide write isolation, signatures or tamper evidence. Required design work
includes local durable staging, removable-media failure behavior, bounded storage,
trusted audit checkpoints, upload acknowledgements and disk-full handling. A hash
chain alone cannot prove that an entire log was not deleted.

## Physical demo and model compatibility

The switch connects the ALICE Pi, Technician Mac, Agent Mac and protected motor
controller; the router provides the enterprise uplink. Disconnecting that uplink
must leave the internal LAN, local addressing, credentials and technician path
usable. Neither a switch nor physical adjacency implements execution enforcement.

The confirmed decision node remains **Pi 4 Model B, 2 GB RAM, OS Lite**. The
reported 64 GB is treated as the storage allocation; confirm the OS architecture
and measured resource use before deployment. The controller choice is still a
second Pi or ESP. Mac training, face processing and the local LLM stay off the Pi.

| Boundary | Existing cyber slice | Required motor/lifecycle follow-up |
| --- | --- | --- |
| Action request | Five cyber actions with fixed parameter semantics. | Motor operation, units, absolute/relative meaning, target and exact retry binding. |
| Normal behavior | Frequencies, known endpoints and transition counts. | Approved position/movement, rate and sequence profiles; operating context and available measurements. |
| Local telemetry | Trusted proposal/execution history supplied to the feature builder. | Authenticated controller observations with timestamps, freshness and availability. |
| Permissions | Runtime remains a skeleton. | Agent/user delegation, mission scope, hard motor bounds, technician capabilities and cache validity rules. |
| Anomaly model | Mac-trained synthetic Web-01 Isolation Forest experiment. | Separately versioned motor feature/model/reference contracts and representative data. |
| Controller | No execution integration. | Current-authority enforcement, idempotency, actual completion and available physical feedback. |
| Activity/audit | No durable mission writer or enterprise connector. | Every offline event, online feed coverage, immutable reconciliation and recoverable upstream delivery. |

Do not add servo angles to the existing 11-column `cyber-behavior-v1` contract.
Keep its fixtures as regression evidence. A commanded position or success receipt
is not an independent sensor observation; report missing physical feedback honestly.

The approved cyber baseline remains routine diagnostics plus occasional changes
to known destinations. Authenticated new agents use a matching role/mission cohort
while preserving novelty. The separately approved diagnostic/change calibration
experiment is documented in the [training guide](anomaly-training.md); it does not
establish a motor profile or a production-ready model.

## Decisions to settle in upcoming implementation slices

- Execution handover: trusted controller/fence owner, transfer messages, in-flight
  commands, loss/recovery thresholds, and behavior when ownership is unknown.
- Enterprise integration: actual source systems, authoritative permission/baseline
  releases, feed coverage, credentials, cache freshness, upload IDs/ACKs and quotas.
- Console agreement: full schema exports, anomaly mapping, authenticated native
  transport, request/parameter-bound remote face proof and execution receipts.
- Motor scope: motor-first with cyber regression coverage, or both demo domains;
  absolute angle versus relative move; controller/sensors; normal and hard bounds.
- Storage: privileged update owner, accepted-generation activation, USB removal,
  durable audit/outbox retention and recovery.

These are open decisions, not implicit approval of example angles, thresholds,
protocols or vendors. The [tracker](implementation-tracker.md) retains all original
118 to-dos and separately tracks requirements introduced by the two-mode design.
