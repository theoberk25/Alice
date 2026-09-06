# Live dashboard and USB storage integration

User-approved scope: the USB carries a versioned synchronized SQL snapshot into
DDIL and receives new offline events. Reconciliation preserves those events and
appends findings/acknowledgements. Pi classifies; Mac resolves held actions after
biometric verification; Pi enforces. Remote review remains unavailable in this slice.

- [x] Add a guarded USB runtime configuration, keeping the existing SQLite ledger,
  hash chain and signing library. Keep the signing key off the transferable drive.
  Validate the selected mount before opening or writing; stop on lost storage.
- [x] Add an authenticated loopback read-only feed bridge that validates the
  existing audit event schema/hashes. Pi access uses SSH forwarding; local tests
  explicitly select a mock controller. No additional database or demo fallback.
- [x] Add a versioned console feed contract, cursor/overlap continuity validation,
  immutable event retention and request grouping. Preserve nulls and provenance.
- [x] Wire the existing dashboard history, workspace, evidence and status panels
  to runtime records; keep fixture review paths separate and remote actions off.
- [x] Test real local request → runtime → bridge → automatic dashboard updates,
  history, malformed events, duplicate/conflict handling and reconnect recovery.
- [x] Update architecture, current snapshot, tracker evidence and Alex's runbook.

Contract mismatches: the REQUEST ledger event omits action/target/parameters;
ASSESSMENT compact projection omits numeric scores. Neither ledger presence nor
HTTP reachability proves evidence verification, model readiness, agent health or
hardware connectivity. Enterprise generator records are a distinct simulated
format. These gaps must render unavailable rather than filling rich fixture fields.

The complete enterprise snapshot publisher and SIEM reconciliation worker remain
outside this display slice; their absence must be explicit, not simulated.

Physical Pi/USB and native Rust acceptance remain pending, as documented in the
[live handoff](../handoffs/2026-09-06-live-dashboard.md). The completed checkboxes
cover implementation and local verification only.
