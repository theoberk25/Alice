# Proposed Dashboard Additions: Agent Management, Machine Overview, and Access Visualization

## Context

The ALICE/DCAMR system operates across four physical components: the **Raspberry Pi** (decision authority), the **Agent Mac** (where local autonomous agents run), the **Technician Mac** (display, explanation, and review), and the **protected endpoints** (firewalls, servers, controllers — the machines agents act upon). When ONLINE, enterprise cloud systems control execution directly and ALICE passively synchronizes context. When OFFLINE/DDIL, the Pi becomes the local decision authority governing agent actions against protected systems.

The existing dashboard scaffolding includes `DecisionView`, `SwarmView`, `ProvenanceTable`, `TechnicianControls`, and `RawDecisionViewer` — all currently empty. The three additions below extend this into a full agent-management system.

---

## 1. Agent Registry Sub-Dashboard

**Purpose:** A single pane showing every agent in the system — where it lives, what it does, and what it has done.

### What it shows

- **Agent identity and hosting location.** Each agent card displays the agent's authenticated ID (e.g., `diagnostic-agent-04`), the physical host it runs on (Agent Mac, cloud/enterprise, or Pi-local), and its current operational status (active, idle, suspended, revoked). The hosting distinction matters: local agents on the Agent Mac propose requests to the Pi during OFFLINE operations, while cloud-hosted agents only operate during ONLINE mode when enterprise systems control execution directly. The card makes this residence explicit — not inferred.

- **Responsible user and mission binding.** Every agent maps to a responsible human user or delegator via the permissions cache. The dashboard shows this attribution chain: which user authorized the agent, under what mission scope, and what delegation bounds apply. Unresolved attribution (an agent whose user mapping can't be verified against trusted data) is flagged visibly, not hidden.

- **Purpose and capability scope.** Each agent's permitted action types (e.g., "read firewall rules," "restart service," "adjust motor position"), hard prohibitions (actions it can never perform regardless of context), and whether it requires technician review for certain operations. This comes from the deterministic permissions layer — the same rules the Pi enforces.

- **Decision history.** A scrollable timeline of every request the agent has made, each tagged with its outcome (`ALLOW`, `REQUEST_CONTEXT`, `HOLD`, `DENY`), the decision factors (which permissions rule applied, what the anomaly score was, whether evidence was available or stale), and provenance (what data sources were consulted at decision time). This reuses the same provenance-first model the architecture requires — every decision factor shows its source. The history distinguishes between ONLINE-observed activity (received via enterprise feeds, where ALICE was not the decision authority) and OFFLINE-governed activity (where the Pi made the call).

- **Behavioral profile.** If the agent has an established normal-behavior baseline, the dashboard shows its familiarity scores: how well-known its action patterns are, which targets it typically interacts with, and its recent action-frequency trends. Agents without a personal baseline (new or rare agents) show their role/mission cohort assignment instead. Anomaly flags from the Isolation Forest scoring are visible here but clearly labeled as behavioral observations, not permission decisions.

---

## 2. Protected Systems / Machine Overview

**Purpose:** A registry of every protected endpoint and machine in the system — the things agents act upon.

### What it shows

- **System inventory.** Each protected system (e.g., `Web-01`, `DB-01`, `AUTH-01`, a motor controller, a firewall appliance) listed with its type, network location, and current execution authority owner (enterprise or ALICE). During ONLINE mode, the enterprise controls these directly; during OFFLINE, the Pi gates access. The dashboard shows which authority regime each machine is currently under.

- **Operational state.** Last-known status from available telemetry: is the system responding, what was its last reported state, when was it last observed. The dashboard is explicit about telemetry freshness — a status reading from 30 minutes ago is labeled as such, not presented as live. Missing telemetry is shown as missing, not inferred.

- **Activity feed per machine.** Every action attempted against this system: which agent requested it, what the request was, what the decision outcome was, whether execution was confirmed, and what the observed effect was. The architecture requires separating request, authorization, attempted execution, completion, and observed consequence — the machine view respects that same chain. A denied request against `DB-01` shows up in `DB-01`'s history just as clearly as an allowed one.

- **Relationship density.** A summary count: how many distinct agents have interacted with this machine, how frequently, and during which mode (ONLINE vs. OFFLINE). This gives the technician a quick sense of which machines are heavily trafficked and which are rarely touched — context that matters when reviewing a held action.

---

## 3. Agent-Machine Access Map

**Purpose:** A visual representation of which agents can access which machines, and which machines have been accessed by which agents — the relationship graph between requesters and targets.

### What it shows

- **Permissions-based access matrix.** A grid or graph where agents are on one axis and protected systems on the other. Each cell/edge shows whether the agent is permitted to interact with that system under current permissions, and if so, what action types are allowed. Hard prohibitions are visually distinct from "allowed with review" and "allowed autonomously." This is the static view: what the rules say, right now.

- **Observed access overlay.** Layered on top of the permissions matrix, the actual history of interactions. An agent that *could* access `Web-01` but never has looks different from one that accesses it 50 times per shift. An agent that accessed a system it shouldn't have (a denied attempt) shows as a flagged anomaly. This is the dynamic view: what actually happened.

- **Directional relationship.** The visualization makes direction explicit. "Agent X requested action on Machine Y" is different from "Machine Y reported telemetry consumed by Agent X's context." The architecture distinguishes agents proposing requests from the Pi forwarding authorized commands to protected endpoints — the map should reflect that agents don't directly touch machines; the Pi (or enterprise, when ONLINE) mediates.

- **Mode-aware filtering.** The technician can filter the map by time window and by operating mode. "Show me all agent-to-machine interactions during the last OFFLINE period" is a natural query when reviewing what happened during disconnection. The map highlights any interactions that occurred during a mode transition — the most security-sensitive moments, when execution authority is transferring between enterprise and ALICE.

- **Anomaly highlighting.** Unusual pairings — an agent accessing a machine it has never touched before, or a sudden spike in interaction frequency — are visually flagged. This draws from the same behavioral feature builder the anomaly engine uses (agent/target familiarity, endpoint relationships, action frequency, five-minute proposal/execution counts), but presents it spatially rather than as a score.

---

## Design Principles (Consistent with ALICE Architecture)

- **Provenance-first.** Every piece of information in these views shows where it came from and when. A decision factor without a source label is a bug.
- **Never rewrite history.** Reassessments and reconciliation events append; original decisions, risk scores, and context availability are preserved exactly as they were at decision time.
- **Mode-aware.** ONLINE and OFFLINE activity are visually and semantically distinct. ALICE doesn't claim to have made decisions it didn't make — enterprise-controlled ONLINE actions are labeled as observed via feed, not as ALICE decisions.
- **Honest about gaps.** Missing telemetry, stale baselines, unresolved attribution, and partial feed coverage are shown explicitly. The dashboard never fills in blanks with assumptions.
- **Complements existing components.** These three views work alongside `DecisionView` (individual decision inspection), `ProvenanceTable` (factor-level detail), and `TechnicianControls` (review actions). The agent registry links to decision details; the machine overview links to provenance; the access map links to both.
