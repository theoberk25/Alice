# Technician console scripts

Install Node 22+ dependencies with `npm ci` at the repository root. Rust stable
and Xcode Command Line Tools are required for native builds. Run these launchers
from any directory using their absolute paths; they discover the checkout from
the root package manifest and preserve `.env`, `.tools/` and npm dependency lookup.

| Launcher | Root npm command | Purpose / outputs |
| --- | --- | --- |
| [desktop.mjs](../../scripts/console/desktop.mjs) | `npm run demo`, `npm run build:app` | Tauri in apps/desktop; builds under apps/desktop/src-tauri/target |
| [rust.mjs](../../scripts/console/rust.mjs) | `npm run test:rust` | Cargo in apps/desktop/src-tauri; forwards CLI arguments |
| [generate-contracts.mjs](../../scripts/console/generate-contracts.mjs) | `npm run contracts:generate` | Runs generate-contracts.ts with installed Vite/Zod and console aliases; writes docs/contracts/*.schema.json and fixtures/alice/*.json |

[paths.mjs](../../scripts/console/paths.mjs) owns checkout discovery. `npm run test:scripts` verifies
launchers in a copied checkout with spaces and an unrelated working directory.
The console imports only its own contracts and services; script consolidation
does not give the renderer access to core policy or execution implementations.
See the [console guide](../guides/technician-console.md).

## Live runtime integration

See [live dashboard setup](../integration/live-dashboard.md) for the authenticated
bridge, USB SQL runtime, remote preview/native configuration and browser test.
The Vite proxy lives with the desktop app; `python -m services.runtime_feed` runs
the read-only bridge. Neither creates a second backend database.
