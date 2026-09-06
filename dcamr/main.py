"""Minimal Pi runtime for the first-light integration test (stdlib HTTP only).

One OFFLINE/DDIL pipeline: authenticate the terminal envelope by verified key,
resolve the exact permission, project a fixture assessment, decide, write the
durable audit trail through dcamr.audit.AuditLog (producer only; the ledger is
never reimplemented here), command the ESP light, and read state back. Retries
of a request_id return the recorded outcome and never execute twice. Everything
else fails closed with DENY/refuse. Scope, placement and preserved-work rules
follow AGENTS.md; the full runtime plan grows these seams later.

The DDIL ledger and evidence live on the selected mounted USB. The private
signing key stays on the Pi. GET /events is the read-only technician feed.
"""

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time
import uuid

from jsonschema import Draft202012Validator, FormatChecker

from dcamr.audit.audit_log import AuditLog, MAX_ATTEMPTS  # noqa: F401 (export for tools)
from dcamr.audit.audit_log import StorageError, SealingError
from dcamr.audit.event_contract import (MAX_EVENT_BYTES, canonical_bytes,
                                        contextual_projection)
from dcamr.audit.signing import Ed25519Signer, Ed25519Verifier, TrustStore, TrustError
from dcamr.decision_model import decide
from dcamr.usb_storage import UsbStorage, StorageUnavailable
from dcamr.enforcement.enforcement_gateway import ControllerError, LightController
from dcamr.packages.package_verifier import load_release
from dcamr.policy_engine.policy_engine import find_permission
from lab.first_light.assessment_fixture import build_assessment

REQUEST_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "common" / "schemas" / "action_request.json"
LEDGER_KEY_ID = "first-light-ledger-key"
AUTHORITY = {"product_mode": "OFFLINE", "connectivity": "DISCONNECTED",
             "execution_owner": "ALICE", "authority_interval_ref": "first-light-interval-1",
             "confirmation": "CONFIRMED"}
# REQUEST..OBSERVED_STATE is at most 7 events; budget with margin so admission
# is refused unless the ledger can hold this request's full outcome set.
EVENTS_PER_REQUEST = 8


class StartupError(RuntimeError):
    """Fail-closed: the runtime refuses to start."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _request_validator():
    schema = json.loads(REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


class FirstLightRuntime:
    def __init__(self, *, release_dir, trusted_manifest_key: bytes, data_dir,
                 esp_base_url: str, usb_root=None, ledger_key_file=None, initialize_ledger=False):
        self.storage = None
        if usb_root is not None:
            try:
                self.storage = UsbStorage(usb_root, data_dir)
                if (ledger_key_file is None
                        or Path(ledger_key_file).resolve().is_relative_to(Path(usb_root).resolve())
                        or not Path(ledger_key_file).is_file()):
                    raise StorageUnavailable("Provision a private ledger key outside USB")
                if not Path(release_dir).resolve().is_relative_to(Path(usb_root).resolve()):
                    raise StorageUnavailable("DDIL release must be on the selected USB")
            except StorageUnavailable as exc:
                raise StartupError(str(exc)) from exc
        try:
            self.release = load_release(release_dir, trusted_manifest_key)
            self._validator = _request_validator()
        except Exception as exc:
            raise StartupError(f"release verification failed: {exc}") from exc

        data_dir = Path(data_dir)
        if self.storage and not initialize_ledger and not (data_dir / "ledger.sqlite").is_file():
            raise StartupError("An existing USB ledger is required; explicit initialization is for first provisioning only")
        (data_dir / "evidence").mkdir(parents=True, exist_ok=True)
        self._evidence_dir = data_dir / "evidence"
        self._boot_id = "boot-" + uuid.uuid4().hex[:12]
        self._lock = threading.Lock()
        self.controller = LightController(esp_base_url)

        seed_path = Path(ledger_key_file) if ledger_key_file else data_dir / "ledger_key.seed"
        if not seed_path.exists():
            seed_path.touch(mode=0o600)
            seed_path.write_text(uuid.uuid4().bytes.hex() + uuid.uuid4().bytes.hex() + "\n")
        seed = bytes.fromhex(seed_path.read_text().strip())
        signer = Ed25519Signer(seed, LEDGER_KEY_ID)
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        public = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        options = dict(signer=signer,
                       trust=TrustStore({("ed25519", LEDGER_KEY_ID): Ed25519Verifier(public)}),
                       clock=self.clock)
        ledger_path = data_dir / "ledger.sqlite"
        try:
            if ledger_path.exists():
                self.ledger = AuditLog.open(ledger_path, **options)
            else:
                self.ledger = AuditLog.initialize(
                    ledger_path, ledger_id="first-light-ledger", node_id="alice-pi-01",
                    quota_bytes=8 * 1024 * 1024, reserve_bytes=256 * 1024, **options)
        except Exception as exc:
            raise StartupError(f"audit ledger unavailable: {exc}") from exc
        if not self.ledger.readiness()["ready"]:
            raise StartupError("audit ledger not ready; refusing admission")
        self._outcomes = {}
        self._rebuild_outcomes()

    # ------------------------------------------------------------------ clock
    def clock(self):
        return {"recorded_at": _utc_now(), "clock_source": "pi-system-clock",
                "confidence": "UNCERTAIN", "boot_id": self._boot_id,
                "monotonic_ns": time.monotonic_ns()}

    # ------------------------------------------------------- event assembly
    def _correlation(self, request_id=None, request_sha256=None, **extra):
        base = dict.fromkeys(("correlation_id", "request_id", "request_sha256",
                              "assessment_id", "action_id", "execution_id", "parent_event_id"))
        if request_id is not None:
            base.update(correlation_id=request_id, request_id=request_id,
                        request_sha256=request_sha256)
        base.update(extra)
        return base

    def _attribution(self, agent_id=None):
        base = dict.fromkeys(("actor_id", "authenticated_requester_id", "agent_id",
                              "responsible_user_id", "delegator_id", "technician_id",
                              "assignment_source_id"))
        base.update(actor_kind="UNKNOWN", resolution="UNRESOLVED")
        if agent_id is not None:
            base.update(actor_kind="AGENT", actor_id=agent_id, agent_id=agent_id,
                        authenticated_requester_id=agent_id,
                        responsible_user_id=self.release.subjects.get(agent_id),
                        assignment_source_id=self.release.bundle_id,
                        resolution="RESOLVED")
        return base

    def _provenance(self, evidence=()):
        artifacts = {name: {"id": None, "sha256": None, "missing_reason": "NOT_APPLICABLE"}
                     for name in ("baseline", "model", "calibration", "snapshot")}
        artifacts["policy"] = {"id": self.release.bundle_id,
                               "sha256": self.release.manifest_sha256, "missing_reason": None}
        artifacts["evidence"] = list(evidence)
        return artifacts

    def _source(self, source_id, source_event_id, available=True):
        return {"source_id": source_id, "source_event_id": source_event_id,
                "observed_at": _utc_now() if available else None,
                "confidence": "UNCERTAIN" if available else "UNAVAILABLE",
                "verification": "UNVERIFIED", "freshness": "UNKNOWN",
                "availability": "AVAILABLE" if available else "UNAVAILABLE"}

    def _append(self, event_id, event_type, *, correlation, attribution, detail,
                evidence=()):
        if self.storage:
            self.storage.check()
        value = {"event_id": event_id, "event_type": event_type,
                 "correlation": correlation, "attribution": attribution,
                 "authority": dict(AUTHORITY), "provenance": self._provenance(evidence),
                 "detail": detail}
        result = self.ledger.append(value)
        if not result.persisted:
            raise StorageError("audit append not persisted")
        if result.sealing_error:
            raise SealingError("audit sealing failed; execution requires recovery")
        return result.event

    # -------------------------------------------------------- outcome memory
    def _record_outcome(self, request_id, request_sha256, response):
        self._outcomes[request_id] = {"request_sha256": request_sha256,
                                      "response": response}

    def _rebuild_outcomes(self):
        for event in self.iter_events():
            correlation = event["correlation"]
            request_id, digest = correlation["request_id"], correlation["request_sha256"]
            if request_id is None:
                continue
            detail = event["detail"]
            if event["event_type"] == "REJECTION":
                self._record_outcome(request_id, digest, {
                    "request_id": request_id, "decision": "DENY",
                    "reason_code": detail["reason_codes"][0], "execution": None,
                    "observed_state": None})
            elif event["event_type"] == "DECISION":
                self._record_outcome(request_id, digest, {
                    "request_id": request_id, "decision": detail["outcome"],
                    "reason_code": detail["reason_codes"][0], "execution": None,
                    "observed_state": None})
            elif event["event_type"] == "EXECUTION_RESULT":
                self._outcomes[request_id]["response"]["execution"] = detail["outcome"]
            elif event["event_type"] == "OBSERVED_STATE":
                self._outcomes[request_id]["response"]["observed_state"] = detail["value"]

    def iter_events(self, after=0):
        if self.storage:
            self.storage.check()
        while True:
            page = self.ledger.read(after=after, limit=64)
            if not page:
                return
            yield from page
            after = page[-1]["sequence"]

    # ------------------------------------------------------------- pipeline
    def _reject_unauthenticated(self, reason):
        self._append("reject-" + uuid.uuid4().hex, "REJECTION",
                     correlation=self._correlation(),
                     attribution=self._attribution(),
                     detail={"outcome": "REJECTED", "reason_codes": [reason]})
        return 401, {"decision": "DENY", "reason_code": reason}

    def handle_request(self, envelope: dict):
        with self._lock:
            try:
                if self.storage:
                    self.storage.check()
                return self._handle_request(envelope)
            except (StorageUnavailable, StorageError, SealingError, OSError):
                if self.storage:
                    self.storage.failed = True
                # Execution may already have begun. Never invent a DENY outcome.
                return 503, {"error": "Storage unavailable; outcome requires reconciliation",
                             "reason_code": "STORAGE_UNAVAILABLE"}

    def _handle_request(self, envelope):
        # 1. Authenticate: identity derives from the verified key, never from
        # the claimed agent_id alone.
        if type(envelope) is not dict or set(envelope) != {"request", "key_id", "signature"}:
            return self._reject_unauthenticated("MALFORMED_ENVELOPE")
        request = envelope["request"]
        try:
            request_bytes = canonical_bytes(request)
            signature = base64.b64decode(envelope["signature"], validate=True)
        except Exception:
            return self._reject_unauthenticated("MALFORMED_ENVELOPE")
        key = self.release.terminal_keys.get(envelope["key_id"])
        if key is None:
            return self._reject_unauthenticated("UNKNOWN_KEY")
        try:
            Ed25519Verifier(key.public_key).verify(signature, request_bytes)
        except TrustError:
            return self._reject_unauthenticated("SIGNATURE_INVALID")
        if next(self._validator.iter_errors(request), None) is not None:
            return self._reject_unauthenticated("SCHEMA_VIOLATION")
        if request["agent_id"] != key.agent_id:
            return self._reject_unauthenticated("AGENT_KEY_BINDING_MISMATCH")

        agent_id = key.agent_id
        request_id = request["request_id"]
        request_sha256 = sha256(request_bytes).hexdigest()

        # 2. Idempotency: a retried request_id returns the recorded outcome and
        # never re-decides or re-executes.
        recorded = self._outcomes.get(request_id)
        if recorded is not None:
            if recorded["request_sha256"] != request_sha256:
                return 409, {"decision": "DENY", "reason_code": "REQUEST_ID_CONFLICT"}
            return 200, dict(recorded["response"], idempotent_replay=True)

        # Admission: refuse unless headroom covers this request's full event
        # set (readiness has no reservation; the runtime budgets its own writes).
        readiness = self.ledger.readiness()
        headroom = (self.ledger._metadata["quota_bytes"] - self.ledger._metadata["reserve_bytes"]
                    - readiness.get("allocated_budget_bytes", 0)) if readiness["ready"] else 0
        if not readiness["ready"] or headroom < EVENTS_PER_REQUEST * 3 * MAX_EVENT_BYTES:
            return 503, {"decision": "DENY", "reason_code": "AUDIT_NOT_READY"}

        correlation = self._correlation(request_id, request_sha256)
        attribution = self._attribution(agent_id)

        # 3. REQUEST
        self._append(f"{request_id}.request", "REQUEST", correlation=correlation,
                     attribution=attribution,
                     detail={"outcome": "ADMITTED", "reason_codes": []})

        # 4. Permission (deterministic; no model in the denial path)
        finding = find_permission(self.release, agent_id, request["action"],
                                  request["target"], request["parameters"],
                                  request_sha256=request_sha256)
        if finding.outcome == "UNRESOLVED":
            self._append(f"{request_id}.rejection", "REJECTION", correlation=correlation,
                         attribution=attribution,
                         detail={"outcome": "REJECTED", "reason_codes": ["NO_PERMISSION"]})
            response = {"request_id": request_id, "decision": "DENY",
                        "reason_code": "NO_PERMISSION", "execution": None,
                        "observed_state": None}
            self._record_outcome(request_id, request_sha256, response)
            self.ledger.seal()
            return 403, response

        # 5. Fixture ASSESSMENT via contextual_projection; the exact bytes are
        # retained as evidence and their sha256 is the evidence binding.
        assessment_bytes = build_assessment(
            request_id=request_id, input_sha256=request_sha256,
            request_at_ms=int(time.time() * 1000))
        evidence_path = self._evidence_dir / f"{request_id}.assessment.json"
        self._write_evidence(evidence_path, assessment_bytes)
        assessment_id = f"{request_id}.a1"
        dispatch = {"assessment_id": assessment_id, "request_id": request_id,
                    "request_sha256": request_sha256, "input_sha256": request_sha256,
                    "execution_id": None,
                    "profile_sha256": json.loads(assessment_bytes)["profile_sha256"],
                    "phase": "PRE_ACTION"}
        evidence_ref = f"assessment-evidence-{request_id}"
        detail = contextual_projection(assessment_bytes, dispatch=dispatch,
                                       evidence_ref=evidence_ref)
        assessment_correlation = dict(correlation, assessment_id=assessment_id)
        self._append(f"{request_id}.assessment", "ASSESSMENT",
                     correlation=assessment_correlation, attribution=attribution,
                     detail=detail,
                     evidence=[{"ref": evidence_ref,
                                "sha256": sha256(assessment_bytes).hexdigest(),
                                "source": self._source("first-light-fixture",
                                                       f"{request_id}.obs")}])

        # 6. DECISION (emitted once per request_id)
        decision = decide(True, finding, detail["status"])
        reason_codes = {decision.reason_code}
        reason_codes.update("GRANT_" + rule.replace("-", "_").upper() for rule in finding.rule_ids)
        self._append(f"{request_id}.decision", "DECISION",
                     correlation=assessment_correlation, attribution=attribution,
                     detail={"outcome": decision.outcome, "reason_codes": sorted(reason_codes)})
        response = {"request_id": request_id, "decision": decision.outcome,
                    "reason_code": decision.reason_code, "execution": None,
                    "observed_state": None}
        if decision.outcome != "ALLOW":
            self._record_outcome(request_id, request_sha256, response)
            self.ledger.seal()
            return 403, response

        # 7. EXECUTION_ATTEMPT must be durably committed before commanding the
        # ESP (AuditLog append is a committed synchronous SQLite write).
        command_bytes = canonical_bytes({"state": request["parameters"]["state"]})
        execution_correlation = dict(correlation, action_id=f"{request_id}.action",
                                     execution_id=f"{request_id}.exec")
        self._append(f"{request_id}.attempt", "EXECUTION_ATTEMPT",
                     correlation=execution_correlation, attribution=attribution,
                     detail={"command_ref": f"{request_id}.command",
                             "command_sha256": sha256(command_bytes).hexdigest(),
                             "outcome": "ATTEMPTED", "reason_codes": []})
        if self.storage:
            self.storage.check()
        try:
            receipt = self.controller.execute(request["parameters"])
            receipt_outcome = "ACCEPTED" if receipt.accepted else "REJECTED"
            available = True
        except ControllerError:
            receipt, receipt_outcome, available = None, "UNKNOWN", False

        # 8. Receipt (transport ack) and result, recorded separately from the
        # independent state readback below.
        self._append(f"{request_id}.receipt", "CONTROLLER_RECEIPT",
                     correlation=execution_correlation, attribution=attribution,
                     detail={"outcome": receipt_outcome,
                             "source": self._source("ESP-LIGHT-01", f"{request_id}.receipt-src",
                                                    available=available),
                             "reason_codes": [] if available else ["CONTROLLER_UNREACHABLE"]})
        result_outcome = "COMPLETED" if receipt_outcome == "ACCEPTED" else (
            "FAILED" if receipt_outcome == "REJECTED" else "UNKNOWN")
        self._append(f"{request_id}.result", "EXECUTION_RESULT",
                     correlation=execution_correlation, attribution=attribution,
                     detail={"outcome": result_outcome,
                             "source": self._source("ESP-LIGHT-01", f"{request_id}.result-src",
                                                    available=available),
                             "reason_codes": [] if available else ["NO_FEEDBACK"]})
        response["execution"] = result_outcome

        # 9. OBSERVED_STATE from a separate readback.
        observed = self.controller.observe()
        observed_bytes = json.dumps({"state": observed.state}).encode("utf-8")
        observed_ref = f"observed-evidence-{request_id}"
        self._write_evidence(self._evidence_dir / f"{request_id}.observed.json", observed_bytes)
        value = None
        if observed.available:
            value = "1" if observed.state == "on" else "0"
        self._append(f"{request_id}.observed", "OBSERVED_STATE",
                     correlation=execution_correlation, attribution=attribution,
                     detail={"asset_id": "ESP-LIGHT-01", "sensor_id": "esp-light-01-readback",
                             "origin": "ACTUATOR_FEEDBACK", "property": "light_state",
                             "value": value, "unit": "bool",
                             "quality": "GOOD" if observed.available else "UNAVAILABLE",
                             "correlation_absence_reason": None,
                             "source": self._source("ESP-LIGHT-01", f"{request_id}.observe-src",
                                                    available=observed.available),
                             "evidence_ref": observed_ref},
                     evidence=[{"ref": observed_ref,
                                "sha256": sha256(observed_bytes).hexdigest(),
                                "source": self._source("ESP-LIGHT-01",
                                                       f"{request_id}.observe-src",
                                                       available=observed.available)}])
        response["observed_state"] = observed.state
        self._record_outcome(request_id, request_sha256, response)
        self.ledger.seal()
        return 200, response

    def _write_evidence(self, path, data):
        if self.storage:
            self.storage.check()
        with path.open('wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def close(self):
        self.ledger.close()


# ------------------------------------------------------------------- server
def make_server(runtime: FirstLightRuntime, host="0.0.0.0", port=8080):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _reply(self, code, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            # The events feed is a read-only projection; allow browser-based
            # technician displays on the LAN to poll it directly.
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != "/request":
                return self._reply(404, {"error": "unknown path"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 64 * 1024:
                    raise ValueError
                envelope = json.loads(self.rfile.read(length).decode("utf-8"))
            except ValueError:
                return self._reply(400, {"error": "invalid body"})
            code, payload = runtime.handle_request(envelope)
            self._reply(code, payload)

        def do_GET(self):
            # Read-only technician feed; no approval verbs are exposed here.
            path, _, query = self.path.partition("?")
            if path != "/events":
                return self._reply(404, {"error": "unknown path"})
            after = 0
            for pair in query.split("&"):
                if pair.startswith("after="):
                    try:
                        after = int(pair[6:])
                    except ValueError:
                        return self._reply(400, {"error": "invalid after"})
            try:
                events = list(runtime.iter_events(after=after))
            except (StorageUnavailable, StorageError, SealingError, OSError):
                return self._reply(503, {"error": "USB ledger unavailable"})
            self._reply(200, {"events": events})

    return ThreadingHTTPServer((host, port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--trust-key", type=Path, required=True,
                        help="hex file with the trusted manifest public key")
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Writable USB directory for SQL ledger and evidence")
    storage = parser.add_mutually_exclusive_group(required=True)
    storage.add_argument("--usb-root", type=Path, help="Existing mounted USB root; no local fallback")
    storage.add_argument("--local-test-storage", action="store_true",
                         help="Explicit local test directory; not physical USB acceptance")
    parser.add_argument("--ledger-key-file", type=Path,
                        help="Provisioned private key outside USB; required with --usb-root")
    parser.add_argument("--initialize-ledger", action="store_true",
                        help="Explicit first provisioning only; never substitutes for a missing SQL snapshot")
    parser.add_argument("--esp-url", required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    trusted = bytes.fromhex(args.trust_key.read_text().strip())
    runtime = FirstLightRuntime(release_dir=args.release, trusted_manifest_key=trusted,
                                data_dir=args.data_dir, esp_base_url=args.esp_url,
                                usb_root=args.usb_root, ledger_key_file=args.ledger_key_file,
                                initialize_ledger=args.initialize_ledger)
    server = make_server(runtime, args.host, args.port)
    print(f"first-light runtime listening on {server.server_address}")
    try:
        server.serve_forever()
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
