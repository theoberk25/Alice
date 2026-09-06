# Native live backend workspace preservation

Updated September 6, 2026. Follow [working rules](../../AGENTS.md).
This records local preservation, not deployment or runtime acceptance.

## Everyday checkout and baseline

Select `/Users/alexdaoud/Documents/Alice` in GitHub Desktop and branch
`codex/native-live-backend`. It is the sole registered Git worktree. The branch
initially started directly at freshly fetched Theodore Berk `upstream/main` commit
`d57c66071b6e8caa1a6c4738d29c3cf765c09925`.
[Biometric PR #4](https://github.com/theoberk25/Alice/pull/4) merged at
2026-09-06 04:41:48 UTC with that merge commit; its delivered head is `ee97ede`.
Final fetch found `de6c6cb`, a documentation-only fan/demo update; the local commits
were rebased onto it with all 437 non-Markdown source entries unchanged. The
biometric commits are ancestors, not duplicated. `origin` is Adaoud03's fork;
its old `main` is not the development baseline. No push or merge was performed.

## Preservation and recovery

Private local preservation directory (ignored by Git):
`/Users/alexdaoud/Documents/Alice/.tools/workspace-preservation-20260906/`.
The earlier `.tools/biometric-integration-backup-20260906/` is unchanged.

| Preserved branch | Meaning |
| --- | --- |
| `codex/live-facial-biometric-upgrade` at `0063629` | Original committed biometric baseline; unchanged |
| `codex/backup-biometric-working-20260906` at `fb7c3d7` | Exact original dirty source/documentation state, including 14 untracked files and intentional tracked deletions |
| `codex/live-runtime-review-wip` at `aa5bae869053403d6e66f336a16b99e55437e404` | Original incomplete backend/native/UI WIP; unchanged |
| `origin/codex/live-face-upstream-integration` at `ee97ede` | Pushed and merged biometric delivery; also preserved in the bundle and upstream ancestry |
| `codex/live-face-port-source` at `be85a87` | Earlier source-port recovery branch |
| `codex/backup-native-interrupted-20260906` at `fc18f80` | Native implementation snapshot recovered after an external GitHub Desktop auto-stash |
| `codex/backup-native-before-upstream-20260906` at `346ee6e` | Focused completed implementation commits before rebasing onto the final upstream documentation update |

The bundle contains all pre-cleanup refs and the snapshot. No stash is needed
for recovery. A separately requested branch-sync task later updated local `main`
to `d57c660` and removed four redundant local refs after creating its own backup;
this native-backend task did not delete those branches. Original biometric, dirty
snapshot, port-source and saved WIP branches remain visible. Local `main` stays at
that task's `d57c660` checkpoint; the active native branch includes the subsequently
fetched `de6c6cb`. `origin/main` is still the fork's older remote branch.
`original-working.patch`, `original-index.patch`, `original-status.z`,
`original-files.json`, `untracked-source.tar.gz`, the copied original handoff and
`verification.json` independently describe the original working state.
An independent bare clone of `all-branches.bundle` reproduced all 81 changed
source/documentation paths; untracked archive members also matched SHA-256.
Ignored private files were never staged. Nineteen settings, model and private
state files were hashed before switching and matched afterward. Existing external
application stores remain in place. Root `.env` was not changed.

Recovery can use `git clone all-branches.bundle /absolute/recovery-folder`, then
select `codex/backup-biometric-working-20260906`; this restores the original source
as a committed tree. The saved base, working/index patches and untracked archive
also reconstruct the original dirty/index distinction. Do not blindly copy an
old source tree onto newer upstream work. Restore private runtime paths only from
their preserved locations and retain their permissions.

## Retired worktrees and dependencies

| Old path below the root | Preserved inactive directory below preservation storage |
| --- | --- |
| `.tools/biometric-main-integration` | `retired-biometric-main-integration` |
| `.tools/biometric-port-source` | `retired-biometric-port-source` |
| `node_modules` | `original-root-node_modules` |
| `.venv` | `original-root-python-venv` |

All 36,475 delivery-tree and 519 port-tree entries retained their inode, size,
mode and symlink target during relocation. Saved worktree administration metadata
and `retired-git-link.txt` retain the old registration information; only stale
registrations were pruned. See `retired-worktree-map.json` for the complete map.
The delivery tree's biometric model/environment symlinks still point at the
unchanged root stores. Retired environment launchers may embed their original
path: these directories are recovery storage, not runnable development checkouts.
Root Node/Python dependencies are rebuilt at their supported original paths.

Before the personal rehearsal, both existing external native SQLite stores were
copied through SQLite's backup API into private preservation storage and passed
`integrity_check`. The rehearsal explicitly reuses the existing enrolled
`console-mock.sqlite3`; it does not reset or replace identities. New native review
tables belong to this existing store. Existing biometric data and models remain
in their original locations.

Before relocation: app-task status showed no other active task, `ps` and `lsof`
identified local services and open files, and Visual Studio Code's saved handoff
tab was closed. `lsof +D` then found no open files in either redundant worktree.
The original local biometric service and old ALICE app were stopped gracefully
before switching source. The old `workstation/` Vite service was separately
inspected: its directory was already absent, although its orphaned process still
held the old inode. It was then stopped gracefully so verification could use this
branch's preview. No worktree or dependency directory was removed under that
process by this session.

The [original continuation handoff](2026-09-06-live-backend-after-biometric-delivery.md)
is now included in root documentation. Its separate-worktree instruction is a
historical recommendation superseded by the user's explicit single-checkout request.

## Concurrent Desktop interruption and recovery

During final validation another task's branch activity coincided with GitHub
Desktop switching this shared checkout to `main` and back. The Git reflog records
those switches at 01:18 EDT. Desktop auto-stash `b03e1c6` removed 53 implementation
paths from the working tree while tests/build were running. Those runs are not
used as final validation evidence.

The stash tree was saved as named branch `codex/backup-native-interrupted-20260906`
at `fc18f80` and bundled in `interrupted-native-work.bundle`. An independent bare
clone reproduced every one of the 53 paths byte-for-byte. The working tree was
restored, later tracker edits preserved, and affected core checks and the native
build rerun successfully. `interrupted-restoration.json` and the saved patch retain
the verification record. Final implementation commits supersede this snapshot;
the exact Desktop stash is removed only after those commits and recovery checks.

The separate branch cleanup report lives under the other task's visualization
directory, `01a07518-71f8-7571-b870-752092050fb7/branch-cleanup-20260906/`.
GitHub Desktop should stay on `codex/native-live-backend` while this checkout is
in use. Backup branches are recovery references, not alternate active checkouts.

## Prior delivery checkpoint (historical)

The following is the saved pre-change current.md. Its tests describe biometric
 delivery only, not the native live backend increment.

```text
# Current
Updated: 2026-09-06 EDT.
Baseline: Theodore Berk's `upstream/main` at `f79cd8e007d02c5abc7b4dffce146e882a51774a`.
Delivery branch: `codex/live-face-upstream-integration`.
Objective: deliver the completed live facial upgrade on the latest team main;
keep unfinished live HOLD review separate and preserve newer team behavior.

## Delivery scope

- Native automatic camera, multi-pose enrollment, ArcFace gallery login, MediaPipe
  pose, MiniFAS presentation checks, encrypted generations and stale/replay guards.
- Enrollment rotates once; login and fresh local fixture approval are automatic.
  Success animation and camera cancellation/lifecycle fixes are retained.
- Deepfake detection is excluded. No detector models, interfaces or fallbacks.
- New team dashboard, read-only live feed, MCP/cloud agents, LLM, Pi/core, hardware,
  network, common contracts and package versions are preserved.
- Live HOLD approve/reject controls remain unavailable. Local fixture approval
  still requires fresh facial verification; it does not command the Pi.
- Unfinished live review is saved locally as `codex/live-runtime-review-wip`
  at `aa5bae8`; it is not part of the delivery or authorized for deployment.
- Original `codex/live-facial-biometric-upgrade` remains at `0063629` with its
  complete uncommitted work unchanged. Backup metadata is under `.tools/`.

## Evidence and limits

Current delivery checks: 117 frontend, 8 script, 166 biometric service and 44 native
Rust tests passed; one live Ollama test intentionally ignored. Core: 362 passed,
266 subtests, one optional serial check initially skipped (follow-up result in report).
Five console E2E tests and one real mock-runtime feed E2E passed. Typecheck, lint,
web build and macOS `ALICE.app` build passed. Public-image ArcFace inference and
retired renderer-frame IPC rejection passed. No integrated human camera acceptance,
physical Pi review, packet-wide monitoring or hardware deployment is claimed.

Historical physical team configuration and evidence are preserved in the
[prior checkpoint](docs/handoffs/2026-09-06-upstream-checkpoint-before-face-integration.md)
and existing [demo runbook](docs/guides/demo-runbook.md). Do not infer new deployment
or authority changes from this source integration. Owners are unassigned.

## Next steps

1. Review the biometric delivery PR; no main merge is authorized.
2. Teammates provision private local models/settings and exercise the built native app.
3. Repeat live enrollment, restart, angled login and fresh local approval with a person.
4. Continue saved live HOLD review separately after delivery; device outputs stay deferred.

[Delivery report](docs/reports/2026-09-06-live-face-main-integration.md) ·
[Facial setup](docs/guides/console/facial-verification-quickstart.md) ·
[Tracker](docs/implementation-tracker.md) · [Rules](AGENTS.md)
```
