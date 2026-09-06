# Backend and live dashboard continuation prompt

Copy the following prompt into the next session.

---

Continue ALICE backend integration and Alex's existing technician dashboard until
it displays actual Pi runtime activity automatically and honestly.

Repository: `/Users/mereksoriano/Downloads/Claude_Code/DN_Hacks/Alice`.
This is a separate nested Git repository; the outer DN_Hacks repo is not the source.

Read AGENTS.md and current.md first. Inspect Git status and fetch remote updates
before editing. Published baseline is `44f4d73` on main, pushed successfully with
user authorization. Local branch was `codex/live-dashboard`. Preserve subsequent
teammate commits, uncommitted handoff documentation, ignored state, keys, runtime
databases and environments. Prior push permission does not authorize future pushes
or deployments. Do not read/search docs/archive or load old conversations.

Then read:

- docs/integration/live-dashboard.md — runnable configuration, mappings and limits.
- docs/handoffs/2026-09-06-live-dashboard.md — verification and implementation handoff.
- docs/reports/2026-09-05-pi-backend-status.md — backend reference, including its correction.
- architecture.md, docs/implementation-tracker.md, relevant console integration
  and contribution guides, and executable contracts.

Inspect current code in dcamr/main.py, dcamr/usb_storage.py,
services/runtime_feed.py, scripts/lab/first_light/, scripts/lab/enterprise_sim/,
published artifacts/enterprise-sim/ examples, apps/desktop/, packages/contracts/
and packages/domain/. Check assessment/audit contracts and current teammate changes.
Jared's enterprise console is separate from Alex's technician dashboard.

What already works:

- Existing SQLite/hash-chain/signing runtime feeds GET /events through an
  authenticated read-only loopback bridge and implemented RemoteAliceTransport.
- Initial history, automatic incremental updates, request/digest correlation,
  duplicates/conflicts, reconnect recovery and unavailable/stale/disconnected states.
- Existing dashboard layout displays runtime decisions and separate execution
  receipts/results/observations. Missing scores and verification remain unavailable.
- USB mount guards and an off-USB private signing key configuration are implemented.
- `npm run demo:live` creates an isolated synthetic SQLite session using the real
  local runtime, fixture assessment and mock ESP. Enter `on`, `off`, or `deny` to
  submit new signed requests. The user saw an allowed request arrive automatically;
  the earlier denied record remained in history. Do not describe that as rewriting
  a denial or as proof of physical Pi connectivity. Previous port 1422 processes
  may have stopped; inspect before reusing or starting them.

Approved storage lifecycle:

The USB carries the latest consistent synchronized SQL snapshot when entering
DDIL/network outage. The Pi reads it and durably records new offline activity on
the USB: decisions, holds, verification evidence and execution outcomes as their
producers become implemented. Reconciliation delivers the original events to SIEM
and appends findings/acknowledgements; it must not rewrite the original audit trail.
The dashboard reads through the Pi service, never by opening the USB database on
the Mac. It remains dynamic while the Mac can reach the Pi, even if upstream
enterprise connectivity is lost. If Mac-to-Pi connectivity is lost, retain known
history, mark it disconnected/stale and recover on reconnection.

Be precise about the implementation gap: USB-backed runtime SQLite exists, but
the enterprise SQL snapshot publisher/import/activation, general SQL-backed policy
loader and SIEM delivery/reconciliation worker do not. First-light still loads a
signed JSON permissions release. Do not call that a completed enterprise snapshot.
Reuse the existing runtime, ledger and signing libraries. Do not add a second
backend database merely because services/backend/ is empty; no logger rewrite,
CBOR migration, or unrelated dashboard redesign.

Physical configuration supplied by the user:

- Host alice-pi-01; Ethernet 192.168.50.20; SSH pi@192.168.50.20.
- USB device /dev/sda; partition /dev/sda1; UUID 6C1A-C6EA.
- Proposed mount /mnt/alice-usb; it was not mounted at the last checkpoint.
- Read-only SSH attempt timed out. Actual filesystem and controller are unverified.

Start physical checks read-only and coordinate with Theo/Jared, who configure the
Pi. Xavi owns hardware; Merek owns backend integration; Alex owns the dashboard.
Do not format the USB, overwrite a ledger/snapshot, copy demo signing keys into
production trust, or deploy over teammates' work without explicit authorization.
Nonsecret connection details can be shared; tokens/private keys stay in local
configuration. Follow the runbook's loopback runtime + SSH tunnel + authenticated
bridge boundary; never place a bearer token in VITE variables or browser code.

Priority and execution:

1. Verify current teammate changes and reproduce the existing local live slice.
   Compile/test the native Rust transport when cargo is available. Identify genuine
   contract mismatches before extending the dashboard; trace every field to a producer.
2. Connect the dashboard to the real Pi feed using the runbook. Verify existing
   USB history and a new signed runtime request updating the dashboard without
   manual refresh. Test reconnect, malformed events, duplicate/conflict handling,
   restart persistence and missing storage/data. Keep fixture/mock labels until
   real assessment/controller producers are connected and verified.
3. Build the next smallest complete backend slice for synchronized SQL snapshot
   creation/validated loading and DDIL operation against Jared's agreed contracts.
   Explain the concrete design briefly, then implement and test it. Preserve audit
   continuity across snapshot changes and never silently initialize over missing
   history. Follow with durable, idempotent SIEM delivery/acknowledgement recovery
   when its actual destination and contract are available. Do not invent delivery.
4. Wire additional dashboard fields only when real producers exist. Pi performs
   ML classification. The Mac resolves held accept/deny after biometric verification;
   backend carries the bound response; Pi validates proof, currentness, permissions,
   authority and audit readiness before execution. Unsupported remote actions
   remain unavailable until that complete path is implemented and tested.

If physical access is unavailable, continue useful implementation/testing with the
real local runtime and explicitly labelled mock controller; ask only genuinely
blocking questions. Never silently fall back to demo records in live mode.

Prior verification at 44f4d73 (rerun as appropriate; not current physical evidence):
276 Python tests and 226 subtests; 73 frontend tests; 5 script tests; typecheck,
lint and production build; 1 live-runtime browser test and 5 existing mock browser
tests passed. Rust tests could not run because cargo was absent. Exact commands
and environment caveats are in the live-dashboard handoff.

Finish each increment with runnable commands, tests actually run, honest remaining
physical/product requirements and an Alex/Jared handoff. Update current.md within
80 lines/800 words and tracker evidence without renumbering tasks. Keep changes
reviewable; request fresh authorization before pushing or deploying.
