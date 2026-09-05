# Synthetic behavioral feature fixtures

These fixtures exercise the first `cyber-behavior-v1` feature builder using
routine Web-01 diagnostics and occasional changes to known destinations. They
contain a synthetic operational baseline and normalized requests with trusted
snapshot examples. They are local lab inputs, not authenticated operational
packages, real traffic measurements, training data, or authorization decisions.

`manifest.json` uses `anomaly-feature-cases-v1`, names the shared `baseline.json`,
and lists each input with its expected ordered feature values and selected profile.
The replay runner computes actual file-byte digests for the loaded fixture files.
The inner `request_sha256` and snapshot `sha256` values are inert correlation
labels; they are not computed body hashes or signatures. No signature-validity
flag or execution mode inside an input establishes trust. The production adapter
must establish trust independently before supplying baseline, identity, and history.

## Feature order

All `expected_values` arrays use this exact order:

1. `agent_known`
2. `action_seen_for_profile`
3. `target_known`
4. `profile_target_seen`
5. `destination_applicable`
6. `destination_seen`
7. `action_frequency`
8. `recent_request_count_5m`
9. `recent_executed_state_changes_5m`
10. `sequence_has_previous`
11. `sequence_transition_probability`

Boolean features use 0/1. A diagnostic request has `destination_applicable=0`
and masked `destination_seen=0`; the latter does not claim an unseen destination.
A complete empty proposal window has `sequence_has_previous=0` and masked
transition probability 0. It is distinct from missing or incomplete history.

## Cases

| Case | Input | Expected comparison |
| --- | --- | --- |
| F01 normal | `input-normal.json` | Known agent requests `query_network` after `query_status`; action frequency 20/100, transition 9/10. |
| F02 known change | `input-known-change.json` | `allow_outbound` to known `10.0.0.10:443/tcp` after `query_network`; frequency 2/100, transition 1/10. |
| F03 new destination | `input-new-destination.json` | Same behavior as F02, with `203.0.113.42:443/tcp` absent from the complete destination list; only destination membership changes. |
| F04 new agent | `input-new-agent.json` | Same diagnostic pattern as F01 for `new-diagnostic-17`; exact role and mission type select `diagnostic-cohort`, while `agent_known` remains 0. |
| F05 session start | `input-session-start.json` | Known agent with a complete empty five-minute history; no previous proposal and no invented transition. |

Every snapshot is observed at `2026-09-05T15:05:00Z`, with history complete since
`15:00:00Z`. Nonempty histories contain two prior proposals, at `15:01:00Z` and
`15:04:00Z`, ordered by their admission ordinal. The current request is not a
history entry. Executions are empty, so the executed-state-change count is zero;
a proposal alone does not prove execution. F02/F03 end with `query_network`;
F01/F04 end with `query_status`.

## Baseline meaning and limits

The two baseline profiles deliberately share the same synthetic counts. The
agent-specific profile applies to `diagnostic-agent-04`; the cohort applies only
to a new agent whose trusted subject has both role `diagnostic` and mission type
`network_investigation`. A fallback does not make the new agent known.

Action counts describe observed frequency, not policy permission. Every supplied
transition row has positive support and is complete: omitted successor actions
have count zero, with no smoothing. The destination relationship compares the
host, port, and protocol tuple. These compact fixtures intentionally omit an
operating-window feature and any unselected sensor features.

Expected feature values verify deterministic lookups and history handling only.
They do not measure anomaly-model quality, set model scores, tune detection
thresholds, approve actions, or demonstrate Raspberry Pi performance. Model
training, package authentication, DCAMR fusion, and hardware acceptance remain
separate increments.
