# Console visual system: sources and motion boundaries

Research verified 2026-09-06. Follow the repository [working rules](../../../AGENTS.md),
[console contribution guide](../console-contributing.md), and current implementation
in `packages/ui/src/`. This document records presentation sources, not application authority.

## Dependencies and permitted reuse

| Dependency or source | License / access | Use in ALICE |
| --- | --- | --- |
| [Motion](https://github.com/motiondivision/motion/blob/main/LICENSE.md) | MIT | Primary React presentation engine: layout, selection, dialogs, transitions, counters, tooltips and button feedback. |
| [Motion Primitives](https://github.com/ibelick/motion-primitives/blob/main/LICENCE.md) | MIT | Selective local adaptations of AnimatedBackground, TransitionPanel, SlidingNumber, BorderTrail and MorphingDialog concepts. No template/framework installation. |
| [Anime.js](https://github.com/juliangarnier/anime/blob/master/LICENSE.md) | MIT | Anime.js draws sparse decorative Face ID contours and morphs the ring into a check; approval retains its Motion ring. |
| [Skiper UI](https://skiper-ui.com/docs/quick-start) | Free components require attribution; premium components have separate access | Visual research only. Its Vercel Tooltip is marked Premium on the public catalog; no Skiper source copied or installed. The ALICE tooltip is original Motion code. |
| [Haikei](https://haikei.app/) | Static SVG/PNG export; asset redistribution rights were not clearly established by the reviewed public terms | Research only. No generated asset, dependency or proprietary geometry copied. |

Installed Motion 13.2.0 and Anime.js 4.5.0 declare MIT in their package manifests
and distributed LICENSE.md files (inspected 2026-09-06). No dependency was added
for the refinement. Local Motion Primitives adaptations were retained from the
reviewed `5bb092a` baseline with the notice below. Motion Primitives is incorporated as
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
  Face ID status copy uses a 55ms exit followed by a 120ms AnimatePresence reveal; exiting copy is
  aria-hidden. Login verification and enrollment opt into size interpolation while
  preserving the camera subtree and leaving its controls unclipped. Other callers,
  including approval, retain their previous defaults.
- [SlidingNumber source](https://github.com/ibelick/motion-primitives/blob/main/components/core/sliding-number.tsx):
  `AnimatedCounter` uses independent fixed-width digit cells with changed-digit
  presence transitions. The accessible value is a single complete text string.
  It is used only for noncritical summaries; the dashboard clock renders static digits.
- [BorderTrail source](https://github.com/ibelick/motion-primitives/blob/main/components/core/border-trail.tsx):
  the retained API now renders only a static neutral surface outline while existing
  async work is active. No beam, moving border or completion callback remains; the
  optional outline is omitted for reduced motion and removed from the camera viewport.
- [MorphingDialog source](https://github.com/ibelick/motion-primitives/blob/main/components/core/morphing-dialog.tsx):
  ALICE retains the native `dialog`, top layer, focus containment, Escape handling,
  immediate close and cleanup. A scoped Tab handler wraps enabled visible controls
  at the first/last focus boundaries. A 180 ms opacity-only opening uses the final
  native geometry; the retained `morphId` attribute no longer scales a camera from a
  small trigger. Closing is immediate; no exit animation delays cancellation or cleanup.

The approval SVG remains unchanged. The separate Face ID SVG uses original ALICE
geometry: exact accepted enrollment evidence, a faint base ring and a vignette.
Login ring stages reflect native acquisition/evaluation/success, not a confidence
score. Only EVALUATING has a moving scan highlight. Eight illustrative points and
sparse contours appear only after native quality PASS; no tracked landmark coordinates
exist in the contract, so these are explicitly decorative, not a measured face mesh.
On authoritative SUCCEEDED the ring finishes in100ms, contours fade inward100–180ms,
and Anime.js morphs the ring180–400ms. Existing450ms acknowledgement (60ms reduced)
and all business timing remain unchanged. No visual callback authenticates or closes.
The older
[Face ID third-party notice](../live-face-third-party-notices.md) is preserved as
historical attribution for the previous circle/check presentation.

Shared timing is centralized in `packages/ui/src/motion-tokens.ts`: press 100 ms,
hover 120 ms, selection 180 ms, panels 160 ms, and dialogs 180 ms. Reduced motion
uses `MotionConfig reducedMotion="user"` plus explicit guards for custom SVG,
digit and imperative animations. No animation completion callback
initiates a console action or a biometric/security state change.

[Motion layout documentation](https://motion.dev/docs/react-layout-animations),
[accessibility](https://motion.dev/docs/react-accessibility), and
[Anime.js React cleanup](https://animejs.com/documentation/getting-started/using-with-react/)
were consulted for the original implementation. The refinement rechecked
[Motion SVG drawing](https://motion.dev/docs/react-svg-animation) and the linked
AnimatedBackground/TransitionPanel sources; the public morphing-dialog page was
unavailable, so existing local implementation and source remained authoritative.
Biometric accepted evidence and terminal
results remain inputs to visual rendering; elapsed time never fabricates progress.

## Focused Face ID morph — 2026-09-06

`FaceIdMorph` adapts the linked Motion Primitives MorphingDialog/Popover pattern
only for login and enrollment. Trigger refs record geometry without replacing any
handler. A blank noninteractive manual popover interpolates to native dialog bounds;
the dialog fades in without transforming or copying camera pixels. The capture is
removed immediately on its existing cancellation/close path. Only disposable empty
chrome may reverse to a still-visible initiating control; no camera subtree is held
by AnimatePresence. Unsupported popovers and reduced motion omit this decoration.

The native dialog retains focus containment, Escape, disabled controls and cleanup.
The prior liquid-glass-react frosted layers below remain, with lower border prominence
and a larger camera. No BorderBeam or additional animation dependency was needed.
Primary source verified through the linked GitHub files (public component pages403):
[Motion layout](https://motion.dev/docs/react-layout-animations) and
[Anime.js morphTo](https://animejs.com/documentation/svg/morphto/).

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


## Earlier Face ID glass adaptation — 2026-09-06

Selected source: [rdev/liquid-glass-react](https://github.com/rdev/liquid-glass-react),
MIT, Copyright 2025 MAX ROVENSKY. The `GlassContainer` backdrop separation and
masked highlight layers in [src/index.tsx](https://github.com/rdev/liquid-glass-react/blob/master/src/index.tsx)
are adapted into `.modal.face-id-dialog` in the biometric stylesheet. This is a
local CSS adaptation, not installation of the entire package. It uses a frosted
28px/140% backdrop, independent screen/overlay edge highlights, soft shadows,
28px corners and sharp foreground content. The camera is never distorted.
The [upstream README](https://github.com/rdev/liquid-glass-react/blob/master/README.md)
notes incomplete Safari/Firefox displacement support; ALICE uses the compatible
frosted layers in native WKWebView. Pointer elasticity/shader displacement are omitted.
At that historical stage, Motion supplied the 180ms dialog fade,160ms instruction transitions and
220ms evidence/check strokes; reduced motion disables decorative transitions.
Reduced transparency makes the glass opaque. No new dependency is added.

License notice retained for the adapted layers:

Copyright 2025 MAX ROVENSKY

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the “Software”), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
