# First-light SQL input snapshot

Follow [AGENTS.md](../../AGENTS.md) and the [live-feed runbook](live-dashboard.md).
This is a bounded local continuation of published checkpoint `44f4d73`.

## Implemented boundary

The publisher captures the five existing first-light release documents, verifies
Ed25519 manifest trust and payload digests, and writes their exact signed bytes
into one SQLite transaction. It validates the completed database, fsyncs it and
publishes with atomic create-if-absent semantics. Existing paths, including
symlinks and racing publishers, are never overwritten. The output parent must
already exist; publication requires hard links and directory/file fsync support.
A failure during directory fsync can leave a complete output with uncertain
publication durability: inspect it; do not overwrite or assume durable success.

The runtime opens SQL read-only, bounds database/document sizes and query work,
checks format/version/document inventory, and reuses the same signature/digest
verifier as JSON-directory loading. No source directory or enterprise connection
is needed after publication. Inputs are captured at startup; there is no hot
reload. The runtime keeps using its existing audit database and signing key.
Snapshot mode requires existing history unless `--initialize-ledger` explicitly
requests first provisioning. Missing/invalid snapshots cannot create history.

This is **signed first-light JSON stored in SQL**, not a general enterprise SQL
policy schema, SQL query-based policy evaluator, live enterprise database backup,
or completed synchronization/activation service. Jared's broader generation-42
example has prohibitions/revocations and lacks the required terminal-key contract;
it is intentionally incompatible. Do not discard those documents to make it load.
No new cross-system contract has been promoted into `common/`.

Snapshot version 1 uses SQLite application ID `0x414c4943`, user version `1`, and
`documents(name TEXT PRIMARY KEY, content BLOB NOT NULL)`. Its exact inventory is
`manifest.json`, `manifest.sig`, `grants.json`, `subjects.json`, `terminal_keys.json`.
Limits are 8 MiB per database and 1 MiB per document. Signature trust is in the
contained release; SQLite layout itself is not a signed identity. The existing
`provenance.snapshot` identifies the verified release bundle and manifest SHA-256,
matching policy provenance. It does not claim an enterprise-wide synchronized state.

## Local commands

From repository root, use an existing verified first-light release and its public
trust key. Choose a **new output filename**. These example variables are paths;
they do not require a private key or token.

```sh
.venv/bin/python -m lab.first_light.publish_snapshot \
  --release "$ALICE_RELEASE_DIR" --trust-key "$ALICE_MANIFEST_PUBLIC_KEY" \
  --output "$ALICE_NEW_SNAPSHOT_PATH"

.venv/bin/python -m dcamr.main \
  --release-snapshot "$ALICE_NEW_SNAPSHOT_PATH" \
  --trust-key "$ALICE_MANIFEST_PUBLIC_KEY" \
  --data-dir "$ALICE_EXISTING_RUNTIME_DATA" --local-test-storage \
  --esp-url http://127.0.0.1:8090 --host 127.0.0.1 --port 8080
```

Run the existing mock ESP in a separate terminal for local tests. Explicitly add
`--initialize-ledger` only for a new isolated test directory or authorized initial
provisioning. On a provisioned Pi replace `--local-test-storage` with `--usb-root`
and supply `--ledger-key-file` outside USB, following the live-feed runbook. Both
the snapshot and runtime data must reside under that USB root. No physical copy,
mount or deployment is performed by the publisher. The dashboard still reads the
runtime through the authenticated bridge; it never opens a USB database itself.

An operator can stop the runtime and select a different verified snapshot path at
restart while retaining the same data directory/key. Prior event bytes, hashes,
request outcomes and queued delivery state survive; new events name the selected
release. Tests exercise a changed release denying a new request while preserving
old allowed history and an explicitly queued test event. There is no delivery
worker or acknowledgement fabricated by this test.

## Remaining agreements and acceptance

Jared: agree full enterprise SQL schema/coverage, identity keys, revocations,
prohibitions, trusted time/freshness, generation rollback anchor and activation
protocol before extending this first-light container. A valid signature alone does
not prove currentness; this slice deliberately makes no rollback/expiry guarantee.
The existing first-light exact-PERMIT semantics and fixture assessment remain.
SIEM destination/authentication/receipt contracts are still needed for delivery.

Alex: existing runtime-feed event schema and read-only transport remain compatible;
new snapshot provenance uses an existing artifact field. Missing scores, physical
verification and remote biometric actions remain unavailable. No UI redesign.

Theo/Jared/Xavi: verify reachability, filesystem, mount, private key provisioning,
physical controller and power-loss/removal behavior. Hard-link publication support
has not been established for USB UUID `6C1A-C6EA`; do not infer its filesystem.

[Implementation and verification handoff](../handoffs/2026-09-06-release-snapshot.md).
