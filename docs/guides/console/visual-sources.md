# Console visual system: sources and motion boundaries

Research verified 2026-09-06. Follow the repository [working rules](../../../AGENTS.md),
[console contribution guide](../console-contributing.md), and current implementation
in `packages/ui/src/`. This document records presentation sources, not application authority.

## Dependencies and permitted reuse

| Dependency or source | License / access | Use in ALICE |
| --- | --- | --- |
| [Motion](https://github.com/motiondivision/motion/blob/main/LICENSE.md) | MIT | Primary React presentation engine: layout, selection, dialogs, transitions, counters, tooltips and button feedback. |
| [Motion Primitives](https://github.com/ibelick/motion-primitives/blob/main/LICENCE.md) | MIT | Selective local adaptations of AnimatedBackground, TransitionPanel, SlidingNumber, BorderTrail and MorphingDialog concepts. No template/framework installation. |
| [Anime.js](https://github.com/juliangarnier/anime/blob/master/LICENSE.md) | MIT | Specialized biometric SVG geometry and timelines only. |
| [Skiper UI](https://skiper-ui.com/docs/quick-start) | Free components require attribution; premium components have separate access | Visual research only. Its Vercel Tooltip is marked Premium on the public catalog; no Skiper source copied or installed. The ALICE tooltip is original Motion code. |
| [Haikei](https://haikei.app/) | Static SVG/PNG export; asset redistribution rights were not clearly established by the reviewed public terms | Research only. No generated asset, dependency or proprietary geometry copied. |

Motion and Anime.js are runtime dependencies. Motion Primitives is incorporated as
small local presentation adaptations with the notice below; no additional runtime
package is required. No Motion+ APIs or paid examples are used. The number primitive
uses fixed digit cells instead of adding `react-use-measure` for one effect.

## Adaptation details

- [AnimatedBackground source](https://github.com/ibelick/motion-primitives/blob/main/components/core/animated-background.tsx):
  `AnimatedSelection` renders a caller-controlled decorative shared-layout span.
  The original clones controls and replaces click handlers; ALICE deliberately keeps
  controls and existing handlers outside the primitive.
- [TransitionPanel source](https://github.com/ibelick/motion-primitives/blob/main/components/core/transition-panel.tsx):
  `TransitionPanel` animates a stable child container when its caller-supplied stage
  changes. A ResizeObserver measures the persistent inner flow-root and Motion
  interpolates the outer height, including surface padding, so native dialog sizing
  follows the content. It does not key/remount the subtree or restart camera capture.
  Unsupported observers retain intrinsic sizing; reduced motion sets height immediately.
- [SlidingNumber source](https://github.com/ibelick/motion-primitives/blob/main/components/core/sliding-number.tsx):
  `AnimatedCounter` uses independent fixed-width digit cells with changed-digit
  presence transitions. The accessible value is a single complete text string.
- [BorderTrail source](https://github.com/ibelick/motion-primitives/blob/main/components/core/border-trail.tsx):
  a masked CSS motion-path accent exists only while the caller reports genuine
  async work. It is decorative, has no completion callback, and is omitted for
  reduced motion.
- [MorphingDialog source](https://github.com/ibelick/motion-primitives/blob/main/components/core/morphing-dialog.tsx):
  ALICE retains the native `dialog`, top layer, focus containment, Escape handling,
  immediate close and cleanup. A scoped Tab handler wraps enabled visible controls
  at the first/last focus boundaries. Optional `morphId` connects its visual opening
  geometry to a trigger marked `data-morph-id`. Native top-layer geometry is used
  instead of replacing authoritative state with the source component's internal
  open state. Closing is immediate; no exit animation delays cancellation or cleanup.

The biometric SVG composition is original ALICE geometry; Anime.js is imported only
by `BiometricScan.tsx` for finite evidence transitions. The older
[Face ID third-party notice](../live-face-third-party-notices.md) is preserved as
historical attribution for the previous circle/check presentation.

Shared timing is centralized in `packages/ui/src/motion-tokens.ts`: press 100 ms,
hover 120 ms, selection 200 ms, panels 220 ms, and dialogs 340 ms. Reduced motion
uses `MotionConfig reducedMotion="user"` plus explicit guards for custom SVG,
offset-path, digit and imperative animations. No animation completion callback
initiates a console action or a biometric/security state change.

[Motion layout documentation](https://motion.dev/docs/react-layout-animations),
[accessibility](https://motion.dev/docs/react-accessibility), and
[Anime.js React cleanup](https://animejs.com/documentation/getting-started/using-with-react/)
were consulted before implementation. Biometric accepted evidence and terminal
results remain inputs to visual rendering; elapsed time never fabricates progress.

## Design reference study

These references informed composition only; no paid screens, templates, product
source code, logos or proprietary assets were redistributed.

| Reference | Public material reviewed | Application to this console |
| --- | --- | --- |
| [Refero](https://refero.design/) | Dashboard, table, dialog, sidebar, tabs and toolbar categories | A dominant decision workspace, narrow type hierarchy, quieter technical metadata and compact dialogs. |
| [Layers](https://layers.to/search/saas-sidebar) | Sidebar collection and individual dark dashboard examples | Low-luminance selected rows, subtle pane boundaries, compact status composition. |
| [Footer.design](https://www.footer.design/) | Dark, Flat, Grid and Small Type categories | Command rail with aligned authority, context and actions; one quiet separating edge. |
| [Manus](https://manus.im/) | Public primary-task and compact secondary-choice presentation | The decision and next existing action remain visually primary. |
| [10x](https://www.10x.app/) and [official repository](https://github.com/10x-app-builder/10x) | Native macOS app and three-pane workspace description | Restrained pane hierarchy and desktop control density; no SwiftUI source reused. |
| [Haikei](https://haikei.app/) | Static grid/export capabilities | Optional faint static geometry only; no Haikei asset included. |
| [Skiper UI](https://skiper-ui.com/) | Tooltip, compact status and control presentation | Fast, quiet original tooltip motion and compact focus treatment. |

Research limitations: public galleries were used; gated research flows and paid
component source were not accessed. Design recommendations are interpretations of
these references, not claims that ALICE duplicates any product's design system.

## Retained Motion Primitives notice

MIT License

Copyright (c) 2024 ibelick

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
