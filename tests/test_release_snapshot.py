"""Signed SQL input snapshots must never replace or reset offline history."""
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest

from dcamr.main import FirstLightRuntime, StartupError
from dcamr.packages import package_verifier
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope


class ReleaseSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="alice-snapshot-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.release = build_release.build(self.root / "bundle")
        self.trusted = bytes.fromhex((self.root / "bundle/trust/manifest_public.hex").read_text().strip())
        self.snapshot = self.root / "permissions.sqlite"

    def publish(self):
        from dcamr.packages.release_snapshot import publish_snapshot
        return publish_snapshot(self.release, self.snapshot, self.trusted)

    def test_sql_roundtrip_preserves_signed_release_and_refuses_overwrite(self):
        from dcamr.packages.release_snapshot import load_snapshot
        self.publish()
        before = self.snapshot.read_bytes()
        self.assertEqual(load_snapshot(self.snapshot, self.trusted),
                         package_verifier.load_release(self.release, self.trusted))
        with self.assertRaises(FileExistsError):
            self.publish()
        self.assertEqual(self.snapshot.read_bytes(), before)
        with sqlite3.connect(self.snapshot) as db:
            raw = db.execute("SELECT content FROM documents WHERE name='grants.json'").fetchone()[0]
        self.assertEqual(raw, (self.release / "grants.json").read_bytes())

    def test_tamper_wrong_trust_missing_and_extra_documents_fail_closed(self):
        from dcamr.packages.release_snapshot import load_snapshot
        self.publish()
        with self.assertRaises(package_verifier.ReleaseError):
            load_snapshot(self.snapshot, b"\x00" * 32)
        missing = self.root / "missing.sqlite"
        with self.assertRaises(package_verifier.ReleaseError):
            load_snapshot(missing, self.trusted)
        self.assertFalse(missing.exists())
        original = self.snapshot.read_bytes()
        for sql in (
            "UPDATE documents SET content=x'7b7d' WHERE name='grants.json'",
            "DELETE FROM documents WHERE name='subjects.json'",
            "INSERT INTO documents VALUES ('extra.json', x'7b7d')",
            "PRAGMA user_version=99",
        ):
            with self.subTest(sql=sql):
                self.snapshot.write_bytes(original)
                with sqlite3.connect(self.snapshot) as db:
                    db.execute(sql)
                with self.assertRaises(package_verifier.ReleaseError):
                    load_snapshot(self.snapshot, self.trusted)

    def test_invalid_release_never_publishes(self):
        (self.release / "grants.json").write_bytes(b"{}")
        with self.assertRaises(package_verifier.ReleaseError):
            self.publish()
        self.assertFalse(self.snapshot.exists())

    def test_publisher_command_uses_existing_trust_and_refuses_existing_output(self):
        command = [sys.executable, '-m', 'lab.first_light.publish_snapshot',
                   '--release', str(self.release), '--output', str(self.snapshot),
                   '--trust-key', str(self.root / 'bundle/trust/manifest_public.hex')]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        original = self.snapshot.read_bytes()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot.read_bytes(), original)

    def test_snapshot_restart_preserves_history_and_does_not_reexecute(self):
        self.publish()
        server, esp = mock_esp.make_server()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        seed = bytes.fromhex((self.root / "bundle/client/term-agent-01-k1.seed").read_text().strip())
        options = dict(release_dir=self.snapshot, release_snapshot=True,
                       trusted_manifest_key=self.trusted, data_dir=self.root / "data",
                       esp_base_url=f"http://127.0.0.1:{server.server_port}")
        with self.assertRaises(StartupError):
            FirstLightRuntime(**options)
        self.assertFalse((self.root / "data").exists())
        runtime = FirstLightRuntime(**options, initialize_ledger=True)
        request = build_envelope(seed, state="on")
        try:
            self.assertEqual(runtime.handle_request(request)[0], 200)
            events = list(runtime.iter_events())
            self.assertEqual(len(events), 7)
            self.assertTrue(all(e["provenance"]["snapshot"]["sha256"] for e in events))
        finally:
            runtime.close()

        # Starting from SQL requires no original release directory or enterprise connection.
        self.release.rename(self.root / "original-release-unused")
        runtime = FirstLightRuntime(**options)
        try:
            self.assertTrue(runtime.handle_request(request)[1]["idempotent_replay"])
            self.assertEqual(esp.commands, 1)
            self.assertEqual(list(runtime.iter_events()), events)
            self.assertEqual(runtime.handle_request(build_envelope(seed, state="off"))[0], 200)
            self.assertEqual(list(runtime.iter_events())[:7], events)
            runtime.ledger.seal()
            runtime.ledger.queue(events[0]['event_id'], 'test-destination')
        finally:
            runtime.close()
        # A different signed release changes future permissions only; pending
        # events and their original provenance/digests remain byte-identical.
        from dcamr.packages.release_snapshot import publish_snapshot
        next_release = build_release.build(self.root / "next-bundle", grant_agent_ids=())
        next_trust = bytes.fromhex((self.root / "next-bundle/trust/manifest_public.hex").read_text().strip())
        next_seed = bytes.fromhex((self.root / "next-bundle/client/term-agent-01-k1.seed").read_text().strip())
        next_snapshot = self.root / 'next-permissions.sqlite'
        publish_snapshot(next_release, next_snapshot, next_trust)
        options.update(release_dir=next_snapshot, trusted_manifest_key=next_trust)
        runtime = FirstLightRuntime(**options)
        try:
            before = list(runtime.iter_events())
            pending = runtime.ledger.pending()
            self.assertEqual(len(before), 14)
            self.assertTrue(pending)
            code, result = runtime.handle_request(build_envelope(next_seed, state='on'))
            self.assertEqual((code, result['reason_code']), (403, 'NO_PERMISSION'))
            after = list(runtime.iter_events())
            self.assertEqual(after[:14], before)
            self.assertNotEqual(after[-1]['provenance']['snapshot']['sha256'],
                                before[-1]['provenance']['snapshot']['sha256'])
            self.assertEqual(esp.commands, 2)
            self.assertTrue(all(item in runtime.ledger.pending() for item in pending))
        finally:
            runtime.close()



if __name__ == "__main__":
    unittest.main()
