# ALICE / DCAMR - Pitch Narrative

Status: matches the actual demo per Jared's runbook update
(`docs/guides/demo-runbook.md`, commit `de6c6cb`, 2026-09-06). Source of
truth for the slide deck, the website, and the on-stage voiceover script. Not
a technical spec; see `docs/prds/ALICE-DCAMR-PRD.md` and
`docs/architecture/contextual-behavior-model.md` for that.

Audience: judges (Booher/DoW, Fanelli/Navy CTO, McCarthy/WH, Fischer/Army),
Second Front track sponsors, general public at table demos.

Revision note: an earlier draft of this narrative used an illustrative
fire/sprinkler two-agent-conflict story. That story does not match what is
actually built (it implied live conflict arbitration between two
simultaneous requests; the real mechanism is behavioral-baseline anomaly
detection on a single request, evaluated against learned history). This
version replaces it with the real fan/power scenario from the runbook, which
has the advantage of being demoable live rather than merely illustrative.

## The story, in one paragraph

Every rule an autonomous agent follows today lives in the cloud: policy
servers, SIEM, EDR, human oversight dashboards. That is fine until the
network goes down, and for defense and critical infrastructure, disconnected,
degraded, intermittent, or limited (DDIL) connectivity is not an edge case,
it is the expected operating environment. When the cloud goes dark, the
agents on the local network do not stop. They keep acting. DCAMR is a local,
offline-first authorization boundary that keeps watching what they do, even
when an individual action is technically permitted, and ALICE is the
technician-facing layer that lets a human make the final call in seconds
when something looks wrong.

## The value add (say this out loud, keep it off the slides)

**Catches accidental-bad, not just malicious-bad, using behavior, not just
rules.** An agent does not have to be compromised or break a rule to cause
harm. It can be fully authorized and still be doing the wrong thing for the
moment, because it does not have the full picture another agent's recent
actions have already created. DCAMR does not just check "is this allowed."
It checks "is this normal, given what has actually been happening," using a
local behavioral baseline that keeps working with zero cloud connection.

## The scenario (this is the real, live demo, not an illustration)

- The base loses connectivity. No SIEM, no policy server, no cloud oversight
  reaches the local network anymore.
- Temperatures climb in a facility bay. `cooling-agent-01` responds exactly
  as trained: three separate `+10%` fan-speed requests, spaced out, each one
  individually unremarkable. DCAMR evaluates each in turn and returns
  `ALLOW`, `ALLOW`, `ALLOW`. This is the learned normal pattern.
- The rising fan speed pushes power draw over a configured threshold.
  `power-agent-01`, a different agent whose job is managing power load, and
  one that is fully authorized to control the fan, requests
  `set_fan_speed(0%)`: an immediate full shutdown.
- Nothing about this request breaks a rule. `power-agent-01` is not
  malicious and not out of bounds. But DCAMR's local behavioral model (an
  Isolation Forest scored against the learned normal pattern for this
  context) sees an abrupt full shutdown, while temperature is still trending
  up, right after a run of small measured increases, and flags it `ELEVATED`
  or `HIGH`. That is not what normal looks like here.
- Because it is not a hard policy violation, this becomes `HOLD`, not
  `DENY`. The local LLM explains the factors it was given (temperature
  still high, an abrupt change against a gradual pattern) and recommends
  rejecting the shutdown. It cannot decide anything itself.
- The technician, identity-verified through ALICE, reviews the one held
  request and rejects it. The fan stays at its last approved, higher level.
  No shutdown happens. All of this, three `ALLOW`s and one rejected `HOLD`,
  is recorded locally while the network is still down.
- When connectivity returns, the queued records upload to the SIEM without
  duplication. Nothing is rewritten. The blackout leaves a complete record,
  not a blind spot.

## What this is not (do not claim these on stage)

- This is not two agents fighting over the same action at the same instant.
  It is sequential: three permitted actions, then one anomalous one, judged
  against the pattern the first three actions established.
- DCAMR is not "mediating a conflict" between agents in the sense of picking
  a winner between two live, competing requests. It is scoring one request
  against a local, learned baseline of normal behavior in this context.
- The anomaly model (`context-behavior-assessment-v1`) is a demo-scale
  Isolation Forest on synthetic fixtures. Say so if asked; do not present
  the fixture's `+10%` steps as a validated production safety envelope.

## Deliberate omissions from the deck (keep these for the live demo or Q&A)

- Deterministic policy vs. anomaly fusion mechanics
- The four machine outcomes and their precedence rules
- Signed package verification and tamper rejection
- Architecture/trust-boundary diagram detail
- Anything from the "Acknowledged Limitations" table in the PRD; bring it up
  only if asked, and answer from that table, not from memory

## Why this fits the track

Second Front sells Game Warden, a DoD-accredited platform for containerized,
offline-capable services. DCAMR is architected that way from the start:
local-first, no cloud dependency for its core decision loop. That is both
the right answer for this problem domain and a direct match for the track
sponsor's platform.

## Close

What is being demoed live today: the ALLOW / HOLD decision sequence above,
running through a simulated DDIL blackout, per
`docs/guides/demo-runbook.md`. Confirm the exact live-vs-narrated split
with the team before presenting, since parts of the native technician app,
Wazuh reconciliation, and physical actuation remain in progress per that
runbook's acceptance checklist.

## Slide-by-slide outline (8-10 slides, ~3 min voiceover)

1. Title / hook: "When the cloud goes dark, who governs your agents?"
2. The shift: agents are already inside operations, already acting.
3. The hidden assumption: every rule they follow lives in the cloud.
4. The blackout: the base loses connectivity, agents keep running.
5. The pattern: cooling agent raises the fan in three small, learned steps.
6. The anomaly: power agent's abrupt full shutdown breaks the pattern.
7. DCAMR sees it: local behavioral baseline flags it, HOLD, not DENY.
8. A human decides: technician rejects the shutdown, decision is logged.
9. The reconnect: nothing is rewritten, the record is complete.
10. Close: built for the environment defense actually operates in; live demo now.

Keep language on-slide short and story-driven. Technical depth comes from
the spoken delivery and the live demo, not the slide text.
