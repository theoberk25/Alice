# Native live backend parity

Updated 2026-09-06. Baseline: merged biometric delivery on Theodore Berk's
`upstream/main`, `d57c660`; active implementation branch `codex/native-live-backend`.
Final fetched upstream `de6c6cb` changes documentation only, preserving the tested
runtime source.
Follow [repository rules](../../AGENTS.md), [technician boundaries](../integration/technician-console.md)
and the [saved-work handoff](../handoffs/2026-09-06-live-backend-after-biometric-delivery.md).

The working technician web app is `apps/desktop/`, served through Vite. Native
ALICE shares its React views, domain state and event schemas. Inventory below is
from executable source, not inferred from fixture screens or planned endpoints.
Local automated results are in the [validation report](../reports/2026-09-06-native-live-backend-validation.md);
physical acceptance is separate.

| Capability | Actual producer / endpoint | Native status and limits |
| --- | --- | --- |
| Web viewer access | `runtime-proxy.mjs`: `GET /api/alice/session`, `POST /api/alice/login`, `POST /api/alice/logout`; 8h cookie, rate limits and same-origin checks | Native uses its own enabled technician session and facial login. Viewer login never grants execution authority. Native feed reads start after sign-in. |
| Live collected traffic and history | Pi `GET /events?after=N` → existing authenticated `services.runtime_feed` bridge → browser `GET /api/alice/events?after=N` or native `read_runtime_events` | Shared history, raw audit details, filtering, request grouping, source and freshness. Coverage is collected ALICE requests/audit events; no packet capture source exists. |
| Immutable decision, assessment and evidence | `alice-audit-event-v1` from the Pi's existing ledger | Shared decision/event timelines, exact digests, evidence provenance and attributed observed identities. Review appends a separate technician record. |
| Request/action/target/parameters | Compact feed has request hash and some assessment context; new `GET /review/<request_id>` returns retained canonical request | Native displays exact supplied request details. Older records without retained bytes remain visible and ineligible. Current upstream request contract is `set_light_state` for mapped ESP targets. |
| Fresh HOLD response | New native proof → existing bridge fixed `POST /review` → Pi verifier | Both approve once and reject require a new action-bound facial scan. Pi owns permission, authority, admission and its original execution path. Web proxy remains read-only. |
| Acknowledgment and delivery uncertainty | Pi review receipt and native durable submission record; `GET /review/<request_id>` returns accepted action identity | Display accepted response separately from controller receipt, execution result and observed state. Preserve outcomes through navigation/feed races; reconcile exact action IDs without retransmitting. An unresolved transmission blocks another review. |
| Reconnect, timeout, malformed data, stale state | Existing cursor/anchor validation, hash-chain checks, bounded bridge/native reads and shared polling | Retain received history during outage with explicit freshness. No fixture fallback. Native history reloads from Pi after app restart; disconnected restart has no local runtime-history mirror. Initial history is capped at 16 MiB; pagination remains upstream work. |
| Current system/agent health | Feed reachability and historical event authority exist; Pi `GET /sync-status` reports Wazuh worker state but web does not expose it | Show only supplied facts. Hardware/engine readiness, current agent health, EDR connectivity and authority transfer are unavailable; HTTP success proves none of these. |
| Rich anomaly scores, reassessment and context exchange | Rich `alice.*` contracts/fixtures exist, but compact feed omits scores; no real context-response receiver | Preserve raw supplied assessment metadata. No synthetic risk scores, local rescoring or invented context delivery. |
| Local explanations | Existing native Ollama gateway explains bounded supplied facts; fixture UI exercises its rich contract | Preserve it. Live brief publication/context exchange is unavailable upstream; explanation cannot approve or execute. |

## Other web and agent surfaces

These remain separate with their existing ownership. They are inventoried so
their working reads and simulated content are not confused with technician parity.

| Surface | Working behavior / source | Integration boundary |
| --- | --- | --- |
| Enterprise SIEM (`scripts/lab/enterprise_sim/console`) | `GET /api/state`: scenario inventory, release/indexer data and labeled local artifact fallbacks. `GET /api/soc?window=all\|24h\|7d`: bounded live Wazuh alert/severity/trend and ledger queries. `GET /api/edge?after=N`: lab Pi feed shortcut. | Separate enterprise view, normally Jared's loopback service. Native has no enterprise read adapter or provisioned authorization. Do not copy its demo credentials/TLS shortcuts, scenario inventory or local artifact fallback into live ALICE. |
| Signed operator workbench (`operator_console.py`) | `POST /action` submits signed agent requests; `GET /status?id=…` correlates Pi and Wazuh records. | Agent-key authority is distinct from technician review. Device output controls remain explicitly deferred. |
| Goose chat (`scripts/lab/goose_chat.py`) | `POST /send` invokes configured local Goose session and existing Light MCP tools. | Separate tool-using agent harness. Preserve current routing; no hidden tool execution through native informational LLM. |
| Light MCP (`services/light_mcp`) | `list_machines`, `get_status`, `set_machine`, `blink`; existing selectable drivers | Preserve existing networking/hardware and mode-aware authority. No second controller path. |
| Decision-Brief MCP (`services/brief_mcp`) | `list_holds`, `get_decision`, `publish_brief`, `get_brief` work with `MockSource` fixture holds/in-memory briefs. Every `AliceSource` method raises `NotImplementedError`. | Live decision source/dashboard publication is genuinely unavailable. Generated briefs carry no authorization. No duplicate HOLD database is introduced. |

`apps/dashboard/src/*`, `dcamr/api/dashboard_api.py`, `services/backend/*.py`,
`services/face_verification/*.py` and `agent/*.py` are retained empty scaffolds.
They are not additional working backend implementations to port.

## Acceptance checklist

- [x] Shared technician web history, evidence and read-only login remain verified by existing browser/bridge and proxy tests.
- [x] Python/native proofs interoperate; replay, restart, concurrent review and uncertain delivery pass local automated checks with synthetic biometric success and mock controllers.
- [x] Frontend tests cover feed-before-ack races, cancellation, stale request/identity, navigation and receipt correlation.
- [x] Build actual `ALICE.app`; preserve local models, enrollments, databases and environment. Successful final rebuild and preservation evidence are recorded in the validation/workspace reports.
- [ ] Personal camera/native/physical-Pi acceptance after separately authorized scoped trust setup and hardware operation.

No push, remote trust provisioning, deployment or hardware acceptance is implied
by local implementation. ONLINE enterprise execution remains unavailable through
local review; OFFLINE eligibility must be independently confirmed by the Pi.

The [validation report](../reports/2026-09-06-native-live-backend-validation.md)
records exact commands, suite counts, interrupted runs and their successful
replacements. Synthetic renderer tests establish UI lifecycle; the separate real
Rust/Python loopback integration establishes signed transport against a mock
controller. Neither establishes human-camera or physical-Pi acceptance.
