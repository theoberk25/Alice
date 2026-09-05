# Contributing

Use Node 22+, Python 3.11, and Rust stable. Run `npm ci` from `workstation/` (the subsystem root), after `cd workstation` from the main repository root. Use `.env` for local settings; never commit credentials, biometric images, enrollment vectors, SQLite data, model weights, or service tokens.

Keep the trust boundary explicit. UI code imports domain interfaces, not network APIs. New inbound events require Zod schemas, versioning, and fixtures. Legacy terminology belongs only in compatibility code and original fixtures. New UI text and commands use ALICE.

Add meaningful tests whenever changing HOLD transitions, upstream decision immutability, action binding, identity verification, replay handling, or language-output validation. Run `npm run check`, the relevant Rust/Python suites, and Playwright when modifying the review flow. Formatting is automated with `npm run format`.

Do not reinterpret policy outcomes in the console, treat agent claims as verified facts, expose model scratchpads, or add hidden LLM tool execution. Do not confuse a console action receipt with execution confirmation. Document console contract changes in `docs/integration/upstream-alice.md` before handing them to another team member. Follow the main [architecture](../docs/prds/ALICE-DCAMR-Architecture.md) and [console integration requirements](../docs/technician-console-integration.md); cross-system contracts require agreement before promotion into `common/`. See the [migration assessment](docs/integration/main-repository-migration.md).
