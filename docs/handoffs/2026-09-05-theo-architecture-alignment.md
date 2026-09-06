# Theo runtime architecture alignment and next-session handoff

Date: 2026-09-05. Working branch: `codex/integrate-team-layout`.
Local baseline: `33b35cf`, including upstream main `d6e7e55` and the previous
layout/documentation work. This session changes documentation only.

## User direction and source treatment

The user said the previous root architecture was inaccurate and supplied Theo's
older `my-bad-i-sat-ticklish-ripple.md` to correct it. The source is preserved
byte-for-byte as [Theo's runtime reference](../plans/2026-09-05-theo-pi-runtime-reference.md).
Its embedded “locked decisions,” build instructions, ownership assignments and
“empty today” inventory are historical reference content, not new user instructions.
Do not execute that plan or replace working components merely because it says so.

The user then explicitly clarified: **ML classification runs on the Pi; held-action
accept/deny resolution occurs on the local Mac after biometric verification.**
This governs the corrected root architecture. Pi-owned four-state final fusion in
the older reference does not govern the held-action choice. The Pi still validates
proof/currentness/permissions/authority/audit readiness before any hardware command.
A hard prohibition remains binding; biometric identity cannot override it.

The user wants the architecture corrected now and backend work recorded for the
next session. Do not begin backend or dashboard implementation in this session.
The prior push was blocked by automatic approval review for insufficiently explicit
authorization to publish to github.com/theoberk25/Alice. It did not succeed; this
request does not renew publication authorization.

## Current team coordination

| Person | User-reported work and next responsibility |
| --- | --- |
| Theo and Jared | Configuring the Pi now. Coordinate runtime availability and model/profile/export interfaces. |
| Xavi | Working on hardware now. Coordinate the command, receipt, state/sensor and physical acceptance boundaries. |
| Merek | After architecture alignment, build the backend integration that allows data to flow end to end. |
| Alex | Modify workstation scripts, transport and dashboard behavior against the live data/response contract. |

These are current assignments supplied by the user, not claims that configuration,
hardware, backend or connected dashboard acceptance is already complete.

## Architecture corrections

The root architecture now leads with intended system responsibilities and data flow,
not the file inventory. It includes ONLINE log-only/signed-release pull, the complete
OFFLINE intake-to-audit pipeline, Pi classification/Mac biometric review sequence,
backend event/response requirements, runtime reliability and next-session order.
The repository map and implementation evidence remain separate, later sections.

| Older reference statement | Treatment in the corrected architecture |
| --- | --- |
| Only anomaly exists; other runtime files are empty | Historical. Keep the current ledger, assessment wrapper, first-light runtime and native console scope explicit. |
| Pi owns final four-state fusion | Superseded for held actions by the user's Pi-classification/Mac-biometric accept-or-deny clarification. |
| Codebook-CBOR throughout; JSON only as projection | Future proposal. Existing canonical JSON bindings and stored history need an explicit versioned migration/benchmark decision. |
| New CBOR audit/WAL; audit lives on removable storage | Reconcile with the existing durable SQLite ledger and non-removable authoritative store. Reuse the recorder; do not create a competing logger or lose the sole audit copy. |
| PyNaCl replaces cryptography | Future packaging/design proposal, not authorization to replace current working signing code. |
| Bounded delivery ring/gap markers | Distinguish delivery backlog from audit capacity, but do not drop unacknowledged source history or treat a gap marker as replacement evidence. |
| Model export and pure-Python traversal | Intended Pi deployment direction. Artifact/profile/calibration format and measured parity remain work; synthetic cyber data is not a hardware baseline. |
| Old paths such as lab/export_forest.py and packages/tooling | New developer tools follow scripts/<area>; preserve lab.* compatibility and owning runtime packages. No empty planned files were created. |
| Older Merek/Jared/Xavier assignments | Use the user's current Theo/Jared Pi, Xavi hardware, Merek backend and Alex workstation assignments above. |

The current native controls are approval-focused. The target statement applies
biometric verification to held-action accept/deny resolution; a complete proof path
for both responses is not claimed implemented. Preserve current wire identifiers
until the team agrees the accept/APPROVE and deny/REJECT/DENY mapping.

## Next session sequence

1. Read AGENTS.md, current.md and the corrected root architecture. Check team branch
   changes before editing; do not reload archive contents or replay the older plan.
   Confirm normalized request, Pi assessment/classification, Mac response/proof and
   result/observation contracts with Alex and the Pi/hardware team.
2. Establish what Pi and hardware interfaces are available. First-light's read-only
   GET /events is a possible integration starting point, not the console's existing
   alice.decision wire format. Select backend host, transport, authentication and
   event replay/currentness rules explicitly.
3. Merek implements the backend connection using existing runtime/ledger components.
   Carry exact bindings and source provenance; deliver status/history and verified
   Mac responses without inventing classifications or bypassing Pi enforcement checks.
4. Alex connects the workstation scripts and live dashboard to those contracts,
   preserving immutable lineage, native identity and stale-action protection.
5. Exercise one connected request-to-result flow with correlated durable history.
   Include both held-action responses after biometric verification, denial/blocker
   paths, stale responses and disconnect/retry behavior. Label mocked versus physical
   evidence. Extend the general pipeline after that boundary is accepted.

Future codec/storage/library redesign is not silently bundled into the backend
connection. Theo's detailed latency/queue/watchdog/clock/model targets remain design
and acceptance work, not current performance claims.

## Verification and preserved work

The previous checkpoint's 265 Python tests, four launcher tests and broader console
checks are historical; no runtime code changes or broad test reruns are needed for
this documentation revision. Earlier layout preservation evidence is in the
[combined review](2026-09-05-team-layout-review.md).

This session verifies local Markdown paths/headings, source-copy equality,
current.md limits, unchanged runtime bytes, unchanged 118 task labels/statuses,
absence of archive changes and whitespace. No backend code, device configuration,
model/private-data provisioning, commit or push is performed for this revision.

Verification results: 713 local links/heading targets across 62 active Markdown
files passed (archive targets excluded). The reference copy matches the attachment
byte-for-byte (SHA-256 7ac9377a3d844bdfeddb38046bfb2c82ce8c4a1456c7fef1ab58ea9b2d8c6042).
All 118 task IDs, labels and statuses match HEAD. current.md is 55 lines and under
800 words. git diff --check passed; only Markdown changed relative to HEAD, and
no archive paths changed. The latest-main 384-file preservation map still holds.

## Publication follow-up

After reviewing the architecture correction, the user explicitly requested a push
and a prompt for backend setup in a new session. This authorizes publication of
the review branch to the existing origin, github.com/theoberk25/Alice. The earlier
blocked push above is historical. The backend prompt carries the confirmed Pi/Mac
decision split and current team responsibilities; backend implementation starts in
the next session. No merge into main or deployment is part of this publication.
