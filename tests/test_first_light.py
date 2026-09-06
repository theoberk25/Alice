"""In-process end-to-end coverage of the first-light acceptance checklist.

Runs the real runtime pipeline against the mock ESP and a temporary ledger:
authentication, exact permission, fixture assessment, auto-approval decision,
durable audit, execution, separate observed state, idempotent retry, ledger
validation after reopen, and the verified USB export. Per AGENTS.md, tests
live in tests/ and reuse the repository's audit contract unchanged.
"""

import base64
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib import request as urlrequest

from dcamr.audit.event_contract import event_hash
from dcamr.main import FirstLightRuntime
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope
from lab.first_light.usb_export import export_request, open_ledger


def _read_all(ledger):
    events, after = [], 0
    while True:
        page = ledger.read(after=after, limit=64)
        if not page:
            return events
        events.extend(page)
        after = page[-1]["sequence"]


class FirstLightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="alice-first-light-")
        root = Path(cls._tmp.name)
        cls.release_dir = build_release.build(root / "bundle")
        cls.trusted = bytes.fromhex(
            (root / "bundle" / "trust" / "manifest_public.hex").read_text().strip())
        cls.seed = bytes.fromhex(
            (root / "bundle" / "client" / "term-agent-01-k1.seed").read_text().strip())
        cls.server, cls.esp = mock_esp.make_server()
        cls._thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls._thread.start()
        host, port = cls.server.server_address
        cls.esp_url = f"http://{host}:{port}"
        cls.data_dir = root / "pi-data"
        cls.usb_dir = root / "usb"
        cls.runtime = FirstLightRuntime(
            release_dir=cls.release_dir, trusted_manifest_key=cls.trusted,
            data_dir=cls.data_dir, esp_base_url=cls.esp_url)

    @classmethod
    def tearDownClass(cls):
        cls.runtime.close()
        cls.server.shutdown()
        cls.server.server_close()
        cls._tmp.cleanup()

    def _envelope(self, **overrides):
        return build_envelope(self.seed, state=overrides.pop("state", "on"), **overrides)

    def test_first_light_checklist(self):
        runtime, esp = self.runtime, self.esp

        # (a) bad signature -> REJECTION, no execution
        bad = self._envelope()
        bad["signature"] = base64.b64encode(b"\x00" * 64).decode("ascii")
        code, payload = runtime.handle_request(bad)
        self.assertEqual((code, payload["decision"], payload["reason_code"]),
                         (401, "DENY", "SIGNATURE_INVALID"))
        self.assertEqual(esp.commands, 0)

        # agent_id must match the verified key's binding
        forged = build_envelope(self.seed, state="on", agent_id="other-agent")
        code, payload = runtime.handle_request(forged)
        self.assertEqual((code, payload["reason_code"]),
                         (401, "AGENT_KEY_BINDING_MISMATCH"))

        # tampering with a signed request fails closed at authentication
        tampered = self._envelope()
        tampered["request"]["parameters"]["state"] = "off"
        code, payload = runtime.handle_request(tampered)
        self.assertEqual((code, payload["reason_code"]), (401, "SIGNATURE_INVALID"))
        self.assertEqual(esp.commands, 0)

        # (b) authenticated request without a covering grant -> NO_PERMISSION
        # (the strict schema pins action/target, so exercise the permission
        # path against a release view with no grants)
        import dataclasses
        original_release = runtime.release
        runtime.release = dataclasses.replace(original_release, grants=())
        try:
            denied = self._envelope()
            code, payload = runtime.handle_request(denied)
        finally:
            runtime.release = original_release
        self.assertEqual((code, payload["decision"], payload["reason_code"]),
                         (403, "DENY", "NO_PERMISSION"))
        rejection = [event["event_type"] for event in _read_all(runtime.ledger)
                     if event["correlation"]["request_id"] == denied["request"]["request_id"]]
        self.assertEqual(rejection, ["REQUEST", "REJECTION"])
        self.assertEqual(esp.commands, 0)

        # (c) happy path -> light on with the full correlated event chain
        envelope = self._envelope()
        request_id = envelope["request"]["request_id"]
        code, first = runtime.handle_request(envelope)
        self.assertEqual(code, 200)
        self.assertEqual(first["decision"], "ALLOW")
        self.assertEqual(first["execution"], "COMPLETED")
        self.assertEqual(first["observed_state"], "on")
        self.assertEqual(esp.state, "on")
        self.assertEqual(esp.commands, 1)
        chain = [event["event_type"] for event in _read_all(runtime.ledger)
                 if event["correlation"]["request_id"] == request_id]
        self.assertEqual(chain, ["REQUEST", "ASSESSMENT", "DECISION", "EXECUTION_ATTEMPT",
                                 "CONTROLLER_RECEIPT", "EXECUTION_RESULT", "OBSERVED_STATE"])
        assessment = next(event for event in _read_all(runtime.ledger)
                          if event["event_type"] == "ASSESSMENT"
                          and event["correlation"]["request_id"] == request_id)
        context = {item["key"]: item["value"]
                   for item in assessment["detail"]["contextual"]["context"]}
        self.assertEqual(context.get("fixture_mode"), "true")
        evidence = Path(self.data_dir) / "evidence" / f"{request_id}.assessment.json"
        self.assertEqual(sha256(evidence.read_bytes()).hexdigest(),
                         assessment["detail"]["contextual"]["assessment_evidence"]["sha256"])

        # (d) identical request_id retried -> one ESP command total, same outcome
        code, second = runtime.handle_request(envelope)
        self.assertEqual(code, 200)
        self.assertTrue(second.pop("idempotent_replay"))
        self.assertEqual(second, first)
        self.assertEqual(esp.commands, 1)
        # same request_id with different content is refused
        conflict = build_envelope(self.seed, state="off", request_id=request_id)
        code, payload = runtime.handle_request(conflict)
        self.assertEqual((code, payload["reason_code"]), (409, "REQUEST_ID_CONFLICT"))
        self.assertEqual(esp.commands, 1)

        # (e)/(f) validate-after-reopen and usb export run in
        # test_zz_usb_export_and_validate against this request's chain.
        type(self)._exported_request = request_id

    def test_zz_usb_export_and_validate(self):
        # Runs after the main checklist (alphabetical ordering within the class).
        request_id = getattr(type(self), "_exported_request", None)
        if request_id is None:
            envelope = self._envelope()
            request_id = envelope["request"]["request_id"]
            code, _ = self.runtime.handle_request(envelope)
            self.assertEqual(code, 200)

        # (f) usb export produces a file whose records match ledger hashes
        out_path = export_request(self.runtime.ledger, request_id, self.usb_dir)
        lines = out_path.read_bytes().splitlines()
        header = json.loads(lines[0])
        self.assertEqual(header["export_format"], "alice-audit-event-v1-ndjson")
        records = [json.loads(line) for line in lines[1:]]
        by_id = {event["event_id"]: event for event in _read_all(self.runtime.ledger)}
        self.assertEqual(len(records), 7)
        for record in records:
            self.assertEqual(record["event_hash"], by_id[record["event_id"]]["event_hash"])
            self.assertEqual(event_hash(record), record["event_hash"])
        # delivery bookkeeping reached ACKNOWLEDGED and nothing was pruned
        self.assertEqual(self.runtime.ledger.pending(), [])
        self.assertEqual(len(by_id), len(_read_all(self.runtime.ledger)))

        # (e) validate passes after seal + reopen
        self.runtime.ledger.seal()
        count = len(by_id)
        self.runtime.close()
        try:
            ledger = open_ledger(Path(self.data_dir))
            try:
                report = ledger.validate()
                self.assertGreaterEqual(report.event_count, count)
            finally:
                ledger.close()
        finally:
            type(self).runtime = FirstLightRuntime(
                release_dir=self.release_dir, trusted_manifest_key=self.trusted,
                data_dir=self.data_dir, esp_base_url=self.esp_url)
            # outcomes were rebuilt from the ledger: retry still does not execute
            commands = self.esp.commands
            envelope = build_envelope(self.seed, state="on", request_id=request_id)
            code, payload = self.runtime.handle_request(envelope)
            if code == 200:
                self.assertEqual(self.esp.commands, commands)

    def test_http_surface(self):
        server = None
        from dcamr.main import make_server
        server = make_server(self.runtime, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            base = f"http://{host}:{port}"
            envelope = self._envelope()
            body = json.dumps(envelope).encode("utf-8")
            request = urlrequest.Request(base + "/request", data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
            with urlrequest.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["decision"], "ALLOW")
            with urlrequest.urlopen(base + "/events?after=0", timeout=10) as response:
                events = json.loads(response.read().decode("utf-8"))["events"]
            self.assertTrue(any(event["correlation"]["request_id"]
                                == envelope["request"]["request_id"] for event in events))
        finally:
            server.shutdown()
            server.server_close()


class PolicyAndDecisionUnitTest(unittest.TestCase):
    """Pure-function coverage for the permission resolver and decide()."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="alice-first-light-unit-")
        root = Path(cls._tmp.name)
        release_dir = build_release.build(root)
        trusted = bytes.fromhex((root / "trust" / "manifest_public.hex").read_text().strip())
        from dcamr.packages.package_verifier import load_release
        cls.release = load_release(release_dir, trusted)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _find(self, agent="term-agent-01", action="set_light_state",
              target="ESP-LIGHT-01", parameters=None):
        from dcamr.policy_engine.policy_engine import find_permission
        return find_permission(self.release, agent, action, target,
                               parameters if parameters is not None else {"state": "on"},
                               request_bytes=b"unit-test-request")

    def test_exact_match_and_denials(self):
        self.assertEqual(self._find().outcome, "PERMITTED")
        self.assertEqual(self._find(parameters={"state": "off"}).outcome, "PERMITTED")
        for finding in (self._find(agent="other-agent"),
                        self._find(action="set_voltage_setpoint"),
                        self._find(target="ESP-LIGHT-02"),
                        self._find(parameters={"state": "blink"}),
                        self._find(parameters={"state": "on", "extra": 1})):
            self.assertEqual(finding.outcome, "UNRESOLVED")
            self.assertIn("NO_PERMISSION", finding.reason_codes)

    def test_decide(self):
        from dcamr.decision_model import decide
        permitted = self._find()
        denied = self._find(target="ESP-LIGHT-02")
        self.assertEqual(decide(True, permitted, "OK").outcome, "ALLOW")
        self.assertEqual(decide(False, permitted, "OK"),
                         type(decide(False, permitted, "OK"))("DENY", "IDENTITY_UNVERIFIED"))
        self.assertEqual(decide(True, denied, "OK").reason_code, "PERMISSION_UNRESOLVED")
        self.assertEqual(decide(True, permitted, "ERROR").reason_code, "ASSESSMENT_UNAVAILABLE")

    def test_package_verifier_fails_closed(self):
        from dcamr.packages.package_verifier import ReleaseError, load_release
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            release_dir = build_release.build(root)
            trusted = bytes.fromhex((root / "trust" / "manifest_public.hex").read_text().strip())
            grants = release_dir / "grants.json"
            tampered = grants.read_bytes().replace(b'"PERMIT"', b'"permit"')
            grants.write_bytes(tampered)
            with self.assertRaises(ReleaseError):
                load_release(release_dir, trusted)
            with self.assertRaises(ReleaseError):
                load_release(release_dir, b"\x00" * 32)


if __name__ == "__main__":
    unittest.main()
