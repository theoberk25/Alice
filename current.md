# Current

Updated: 2026-09-05
Local baseline: `33b35cf`; includes main `d6e7e55` and prior documentation/layout work.
Review branch: `codex/integrate-team-layout`; architecture correction and handoff.
User authorized branch publication to github.com/theoberk25/Alice after the correction.
Earlier checkpoint `011abf1` remains separate; do not replay its obsolete layout.

## Current objective

Use the corrected architecture and next-session handoff to begin backend setup
in the next session. The current task publishes the review branch and prepares
the session prompt; it does not implement the backend. Start with [AGENTS.md](AGENTS.md).

## Confirmed architecture and coordination

- **Pi: ML classification. Local Mac: held-action accept/deny after biometric
  verification. Pi: validate the bound response and enforce execution prerequisites.**
  A hard prohibition remains binding; LLM prose/biometrics cannot override it.
- Theo and Jared are configuring the Pi; Xavi is working on hardware.
- Merek will build end-to-end backend data flow after architecture alignment;
  Alex will adapt workstation scripts/transport/dashboard to the agreed live contract.
- Root architecture now defines target pipeline, backend flows, storage/model and
  reliability requirements, current implementation limits and the source map.
- Theo's older plan is preserved as reference, not executable instructions. CBOR,
  codebooks, signing-library changes and removable audit storage require agreement.
- First-light remains a signed-request/fixture-assessment/mock-ESP slice; the console
  has working fixture workflows but its remote transport is not connected.
- All 118 tracker IDs/statuses stay unchanged: 12 done components, 38 partial, 68 planned.

## Next session

1. Confirm request/classification, Mac accept/deny proof and hardware-result bindings
   with Alex and the Pi/hardware team, preserving the confirmed decision ownership.
2. Check Theo/Jared's Pi readiness and Xavi's device interface; select backend host,
   transport, authentication and replay/currentness contracts before implementing.
3. Merek builds the backend connection using the existing runtime/ledger boundaries.
4. Alex connects workstation scripts and the live dashboard, preserving native
   identity, immutable lineage and stale-response guards.
5. Validate one connected request/review/result flow and both biometric-gated held
   responses, then extend context, recovery and enterprise synchronization.

## Verification and limits

Documentation checks passed: 713 local links/headings, byte-identical reference copy,
118 tracker rows preserved, current.md within limits and no runtime/archive changes.
Prior 265 Python tests (zero skips), launcher and console checks are historical;
no new runtime, native, camera, Pi/hardware or live-enterprise acceptance is claimed.
[Alignment and next-session handoff](docs/handoffs/2026-09-05-theo-architecture-alignment.md) ·
[Previous verification](docs/handoffs/2026-09-05-team-layout-review.md).

## Start here

[Rules](AGENTS.md) · [Architecture](architecture.md) · [Docs](docs/README.md) ·
[Tracker](docs/implementation-tracker.md) · [Scripts](docs/scripts/README.md)
