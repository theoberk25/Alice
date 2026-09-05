# WIP core components — workflow integration handoff

This checkpoint combines the reviewed core ledger and model-to-ledger replay with
Jared's enterprise simulation from `origin/main` at `1e84a9f`. It is shared for
Theo's workflow planning and integration, not as completed live-system acceptance.
The user authorized merging and pushing this WIP checkpoint to `main`; earlier
local-only restrictions in historical handoffs are superseded for this publication.


## Subsequent Pi assessment increment

`dcamr/decision_model.py` now implements the
[technician-application assessment boundary](../contracts/decision-assessment.md); it is no
longer an empty skeleton. This combines trusted permission findings and contextual
scores without choosing a final decision. The local LLM interprets the evidence;
unusual actions require human approval enforced outside the LLM. The ledger's
existing contextual projection and this assessment are distinct contracts:
transport/ledger owners must bind them explicitly rather than inserting the full
packet into the compact ledger schema. No new audit implementation is introduced.


## Ownership and coordination

| Work | Owner / boundary |
| --- | --- |
| Workstation and downstream dashboard | Alex; preserve its native identity and approval flows. |
| Online enterprise/SIEM simulation and agent permissions | Jared; use his release formats and fixtures as integration inputs. |
| Workflow planning and integration | Theo; compare his existing scripts with these entry points before adding or consolidating implementations. |
| Core anomaly features, training/scoring and local durable ledger | Components contributed by this work; reuse their existing validation and persistence APIs. |

Theo's current scripts have not been compared here. Potential duplication is
accepted temporarily; assess actual behavior, input/output contracts, dependencies
and tests before removing either implementation. No teammate code was rewritten
as part of this merge.

## Reuse these components

| Purpose | Entry point | Boundary |
| --- | --- | --- |
| Cyber baseline and feature extraction | `dcamr/anomaly_engine/baseline.py`, `features.py` | Supplied bytes/digests and captured history; does not authenticate releases or inputs. |
| PRE/POST observation validation | `dcamr/anomaly_engine/context_profile.py` | Explicit profile, phase, units, timestamps, context and source identities. |
| Contextual training and assessment | `lab/contextual_training.py`, `dcamr/anomaly_engine/contextual_model.py` | In-memory models, exact-context routing, UNKNOWN on unavailable input/model; no permission decision. |
| Compact assessment recording | `dcamr/audit/event_contract.py:contextual_projection` | Capture dispatch before inference; retain exact assessment bytes externally, reference their digest. |
| Durable history and delivery state | `dcamr/audit/audit_log.py:AuditLog` | Explicit initialize/open, append, seal, queue, attempts, ACK and reconciliation markers; no sender. |
| Executable model-to-ledger example | `lab/replay_contextual_ledger.py` | Six synthetic cases, temporary evidence/test key, anchored restart and duplicate retry. |
| Enterprise simulation | `lab/enterprise_sim/`, [Jared's handoff](enterprise-sim-handoff.md) | Demonstration permissions/releases, datasets, Wazuh configuration and authored activity; not a live Pi runtime. |
| Technician console | `workstation/`, [integration guide](../guides/workstation.md) | Local UI/native services; remote actions remain blocked until transport is implemented. |

## Compare before connecting

- The enterprise simulation's `alice-audit.jsonl` chain, the ledger's
  `alice-audit-event-v1`, and workstation `alice.decision` contracts are distinct.
  The enterprise activity generator and ledger both use the version string
  `alice-audit-event-v1` despite incompatible envelopes and hash rules; that string
  alone cannot select the correct parser. Disambiguate the producer/format at the
  integration boundary before ingesting either stream.
  Do not treat their JSON, hashes or signatures as interchangeable. Choose an
  explicit mapping and preserve exact original bytes/digests where needed.
- Ledger Ed25519 checkpoints attest stored history. They are not signed permission
  releases, biometric approval proofs or deployable model artifacts. The model's
  in-memory fingerprint is not a signed artifact digest.
- Simulation signing keys are public demonstration material. Production trust/key
  provisioning remains separate; never install those demo keys as production trust.
- The ledger records supplied claims; it does not authenticate an actor, feed,
  receipt or sensor by accepting its identifier or verification flag.
- Normal-work readiness is not reserved storage for an admitted action. The future
  workflow must budget durable outcome writes and handle recorder failures before
  consequential execution. Delivery ACKs do not authorize deletion or execution.
- ONLINE enterprise execution and OFFLINE endpoint-enforced transfer remain separate.
  Connectivity loss, a technician click or a signed record alone grants no control.

## Remaining workflow work

Compare Theo's implementation against request admission, permissions resolution,
anomaly/permissions fusion, bounded context exchange, technician approval binding,
endpoint authority transfer and execution, actual outcome acquisition, and
reconnect delivery/reconciliation. Their core placeholder files in this checkout
are not proof those capabilities are absent from teammates' working branches.

Model save/load, trusted release activation, production evidence retention and Pi
memory/latency/power-loss acceptance remain outstanding here. Real sensor operating
data and safe limits are not established by either synthetic fixture collection.

## Local checks

From the repository root with audit and training dependencies installed:

```sh
.venv/bin/python -m unittest discover -v
.venv/bin/python -m lab.replay_anomaly_fixtures
.venv/bin/python -m lab.replay_feature_fixtures
.venv/bin/python -m lab.replay_contextual_ledger
```

For fresh enterprise/training setup, follow Jared's Python 3.12 instructions in
his handoff. Workstation has its own Node/Rust/Python environments and test suites;
the root Python suite does not cover the workstation runtime or live Wazuh.

Verification on the combined tree (Python 3.13.2 in the existing local environment):
236 tests passed with zero failures/errors/skips; all three replays passed
(8 anomaly fixtures, 7 score cases, 5 feature vectors, 6 ledger assessment cases).
The enterprise generator also passed in a temporary output directory: 15 baseline
profiles, 50 PRE and 50 POST observations parsed, valid cohort fallback and intact
audit chain, with no validation failures. This does not rerun live Wazuh, workstation
camera/native acceptance or the full enterprise fitting experiment.
