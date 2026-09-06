# Dashboard visual refinement specification

Approved scope: 2026-09-06. Follow [working agreements](../../AGENTS.md),
[console contribution rules](../guides/console-contributing.md), and
[live state](dashboard-visual-refinement-live-state.md). Baseline: `5bb092a`.

## Scope and invariants

Refine the current ALICE desktop presentation into a restrained industrial/security
UI. Preserve authentication, authorization, HOLD/DENY, grants, handlers, available
controls, navigation, focus/keyboard/dialog interactions, contracts, persistence,
networking, hardware, and all biometric algorithms, thresholds, challenges,
capture/completion requirements, camera lifecycle, cancellation and mirroring.
No push, merge, deployment, unrelated refactoring or new product features.

The sole functional exception is the dashboard clock: current device system time
and configured local IANA zone, 24-hour HH:mm:ss using h23, automatic DST, accurate
zone indicator with IANA/offset disambiguation, immediate foreground/resume refresh
and automatic zone-change detection. Sample current wall time every update; format
time/date/zone from the same instant and zone. No network/location/device-setting
changes or changes to stored, audit or other displayed timestamps.

## Presentation decisions

- Stable responsive 16:9 camera viewport across startup, preview, processing,
  success and errors. Native camera prefers 640×360; 640×480 fallback stays fully
  visible with `object-fit: contain`. No frame retention, crop, zoom, blur, tilt,
  stretching, animation-induced mounting, or image-driven aspect-ratio changes.
- Current instruction first; reserve status space. Camera/pose feedback precedes
  completed/remaining angles, then supporting explanation and existing Face ID
  checks disclosure. Keep cancellation and content above the fixed command rail.
- Preserve ring segment placement and coverage count/2 calculations. Neutral
  outstanding segments, restrained cyan evidence, finite 180–240 ms acceptance
  acknowledgment, static settled completion. Emphasize existing incomplete chips;
  when one remains show its real label (for example, “Left still needed”). Preserve
  any-order capture and own-left/right semantics. No invented landmarks/challenges.
- Horizontal bar remains the sum of accepted coverage counts /14; angle completion
  counts only regions with two samples. The accepted-observations label separately
  reports backend `accepted_samples`. Make those meanings explicit and subordinate.
- Authoritative status/result text updates synchronously. Decorative status fades
  120–180 ms, travel at most 4–6 px; no delay, debounce or animation-gated actions.
  Preserve existing acknowledgment/dismissal timing and verification/grant meaning.
- Improve secondary contrast, selected history rows, aligned administration rows,
  rail separation/clearance, and one navigation selection surface (140–200 ms).
  Dialogs use a modest surface fade, retaining native dialog interaction ownership.
- Reuse installed Motion and local MIT Motion Primitives adaptations. Prefer Motion
  for simple SVG acknowledgments; no new dependency, paid code, border beams,
  particles, glows, fake meshes or perpetual scan ornamentation. Retain notices.
- Reduced motion uses static states/brief fades, retaining functional live preview,
  visible focus, readable statuses and keyboard access. Never animate security
  values, identifiers, timestamps or the clock; existing summary counts may remain.

## Acceptance evidence

Capture baseline and refined synthetic screens at 1512×1040 and smaller supported
sizes (1280×720, 1024, 800 and 390 wide; admin rows also at 520 wide). The referenced recording was not attached; exact
recording dimensions and real camera acceptance cannot be claimed. Test viewport
stability, remaining poses, immediate results/cancellation, controller identity,
reduced motion, dialog focus/Escape/outside-click and content clearance. Run existing
console/security interaction regressions without weakening production checks.
Add focused clock tests for Eastern winter/summer, another zone, midnight,
time/date/zone agreement, and resume/device-zone changes. Record commands actually
run and distinguish synthetic/component checks from real camera/physical acceptance.
