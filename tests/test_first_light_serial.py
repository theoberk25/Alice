"""Coverage for the USB-serial light transport and its runtime integration.

Exercises the real SerialLightController logic against the protocol simulator in
lab.first_light.mock_esp_serial (no hardware, no pyserial), plus one PTY test
that runs the same controller over a real serial.Serial when the optional
dependency is installed. Per AGENTS.md, tests live in tests/ and reuse the
repository's audit contract unchanged; the HTTP transport keeps its own
coverage in test_first_light.py.
"""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from dcamr.enforcement.enforcement_gateway import ControllerError
from dcamr.enforcement.serial_light_controller import SerialLightController
from dcamr.main import FirstLightRuntime, StartupError, _make_controller
from lab.first_light import build_release, mock_esp_serial
from lab.first_light.terminal_client import build_envelope

HAS_PYSERIAL = importlib.util.find_spec("serial") is not None
ROOT = Path(__file__).resolve().parents[1]


def _controller(timeout=0.2):
    transport, esp = mock_esp_serial.make_loopback()
    return SerialLightController("loopback", timeout=timeout, transport=transport), transport, esp


class SerialProtocolTest(unittest.TestCase):
    """Transport-level behavior against the protocol simulator."""

    def test_set_on_and_off_are_acknowledged(self):
        controller, _, esp = _controller()
        receipt = controller.execute({"state": "on"})
        self.assertEqual((receipt.accepted, receipt.status_code), (True, None))
        self.assertEqual((esp.state, esp.commands), ("on", 1))
        receipt = controller.execute({"state": "off"})
        self.assertTrue(receipt.accepted)
        self.assertEqual((esp.state, esp.commands), ("off", 2))

    def test_exchange_never_calls_unbounded_flush(self):
        controller, transport, _ = _controller()
        def forbidden_flush():
            raise AssertionError('flush can wait indefinitely outside write_timeout')
        transport.flush = forbidden_flush
        self.assertTrue(controller.execute({'state': 'on'}).accepted)

    def test_continuous_unterminated_bytes_stop_at_deadline_without_line_buffer_growth(self):
        class NoisyTransport:
            reads = 0
            def write(self, data): return len(data)
            def readline(self):
                raise AssertionError('unbounded readline must not be used')
            def read(self, size):
                self.reads += 1
                if size != 1: raise AssertionError('read must have a fixed bound')
                return b'x'
        transport = NoisyTransport()
        controller = SerialLightController('noise', timeout=.03, transport=transport)
        start = time.monotonic()
        with self.assertRaises(ControllerError): controller.execute({'state': 'on'})
        self.assertLess(time.monotonic() - start, .5)
        self.assertGreater(transport.reads, 0)

    def test_malformed_matching_reply_cannot_claim_completed(self):
        for changes in ({'v': True}, {'boot_id': None}, {'boot_id': 'not-a-boot-id'}):
            with self.subTest(changes=changes):
                controller, _, esp = _controller(timeout=.02)
                original = esp._ok
                esp._ok = lambda command_id: dict(original(command_id), **changes)
                with self.assertRaises(ControllerError):
                    controller.execute({'state': 'on'})

    def test_serial_timeout_must_be_finite_positive_and_bounded(self):
        for timeout in (0, -1, float('inf'), float('nan'), 11):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                SerialLightController('unused', timeout=timeout)

    def test_late_newline_is_unknown_but_does_not_discard_next_exchange(self):
        controller, transport, esp = _controller(timeout=.02)
        original_read = transport.read
        def late_newline(size):
            raw = original_read(size)
            if raw == b'\n': time.sleep(.03)
            return raw
        transport.read = late_newline
        with self.assertRaises(ControllerError): controller.execute({'state': 'on'})
        transport.read = original_read
        self.assertTrue(controller.execute({'state': 'off'}).accepted)
        self.assertEqual(esp.commands, 2)

    def test_observe_reads_back_without_mutating_output(self):
        controller, _, esp = _controller()
        controller.execute({"state": "on"})
        self.assertEqual(esp.commands, 1)
        observed = controller.observe()
        self.assertEqual((observed.available, observed.state), (True, "on"))
        # A readback is not a write: the device command counter must not move.
        self.assertEqual(esp.commands, 1)

    def test_explicit_device_rejection_is_not_unreachable(self):
        controller, _, esp = _controller()
        esp.reject_next = 1
        receipt = controller.execute({"state": "on"})
        # Reached and declined -> REJECTED/FAILED, never UNKNOWN.
        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.body["error"], "INVALID_COMMAND")
        self.assertEqual((esp.state, esp.commands), ("off", 0))

    def test_acknowledgment_with_the_wrong_state_is_refused(self):
        controller, _, esp = _controller()
        esp.wrong_state_next = 1
        receipt = controller.execute({"state": "on"})
        self.assertFalse(receipt.accepted)

    def test_invalid_frames_are_rejected_without_touching_the_output(self):
        transport, esp = mock_esp_serial.make_loopback()
        cases = [
            (b'{"v":2,"id":"a","op":"set","state":"on"}\n', "BAD_VERSION"),
            (b'{"v":true,"id":"a","op":"set","state":"on"}\n', "BAD_VERSION"),
            (b'{"v":1,"id":"a","op":"set","state":"off","state":"on"}\n', "MALFORMED"),
            (b'{"v":1,"id":"a","op":"blink","state":"on"}\n', "BAD_OP"),
            (b'{"v":1,"id":"a","op":"set","state":"dim"}\n', "BAD_STATE"),
            (b'{"v":1,"id":"a","op":"set","state":"on","extra":1}\n', "UNKNOWN_FIELD"),
            (b'{"v":1,"id":"a"}\n', "MISSING_FIELD"),
            (b'{"v":1,"id":"a","op":"get","state":"on"}\n', "UNKNOWN_FIELD"),
            (b'not json at all\n', "MALFORMED"),
            (b'{"v":1,"id":"a","op":"set","state":"on","pad":"' + b"x" * 300 + b'"}\n',
             "LINE_TOO_LONG"),
        ]
        for frame, expected in cases:
            with self.subTest(expected=expected):
                transport.write(frame)
                reply = json.loads(transport.readline())
                self.assertEqual((reply["ok"], reply["error"]), (False, expected))
        self.assertEqual((esp.state, esp.commands), ("off", 0))

    def test_truncated_frame_is_discarded_and_the_next_reply_is_used(self):
        controller, transport, esp = _controller()
        # A truncated but newline-terminated reply left in the buffer: dropped,
        # and the real acknowledgment on the next line is still matched.
        transport.feed(b'{"v":1,"id":"torn","ok":tr\n')
        receipt = controller.execute({"state": "on"})
        self.assertTrue(receipt.accepted)
        self.assertEqual(esp.state, "on")

    def test_unterminated_fragment_costs_one_command_then_resynchronizes(self):
        controller, transport, esp = _controller()
        # Bytes lost mid-frame with no newline: they merge with the next reply
        # into one unusable line, so that exchange is UNKNOWN. The stream
        # resynchronizes at the following newline and the next command works.
        transport.feed(b'{"v":1,"id":"torn","ok":tr')
        with self.assertRaises(ControllerError):
            controller.execute({"state": "on"})
        receipt = controller.execute({"state": "off"})
        self.assertTrue(receipt.accepted)
        self.assertEqual(esp.state, "off")

    def test_command_written_in_fragments_is_still_one_command(self):
        transport, esp = mock_esp_serial.make_loopback()
        frame = b'{"v":1,"id":"split-1","op":"set","state":"on"}\n'
        for index in range(len(frame)):
            transport.write(frame[index:index + 1])
        reply = json.loads(transport.readline())
        self.assertEqual((reply["ok"], reply["state"]), (True, "on"))
        self.assertEqual(esp.commands, 1)

    def test_stale_reply_ids_are_discarded_not_accepted(self):
        controller, transport, esp = _controller()
        transport.feed(b'{"v":1,"id":"someone-else","ok":true,"state":"off","boot_id":"aa"}\n')
        receipt = controller.execute({"state": "on"})
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.body["state"], "on")

    def test_mismatched_reply_id_times_out_as_unknown(self):
        controller, _, esp = _controller()
        esp.wrong_id_next = 1
        with self.assertRaises(ControllerError):
            controller.execute({"state": "on"})
        # The device did apply it; the Pi simply cannot prove that. The runtime
        # records UNKNOWN rather than success or failure.
        self.assertEqual(esp.state, "on")

    def test_dropped_acknowledgment_raises_controller_error(self):
        controller, _, esp = _controller()
        esp.drop_next = 1
        with self.assertRaises(ControllerError):
            controller.execute({"state": "on"})

    def test_disconnected_device_is_explicit_failure(self):
        controller, transport, _ = _controller()
        transport.offline = True
        with self.assertRaises(ControllerError):
            controller.execute({"state": "on"})
        # observe() never raises; it reports unavailability instead.
        observed = controller.observe()
        self.assertEqual((observed.available, observed.state), (False, None))

    def test_malformed_reply_then_valid_reply_recovers(self):
        controller, _, esp = _controller()
        esp.malformed_next = 1
        receipt = controller.execute({"state": "on"})
        self.assertTrue(receipt.accepted)

    def test_missing_pyserial_is_reported_not_silently_skipped(self):
        controller = SerialLightController("/dev/does-not-exist", timeout=0.1)
        with self.assertRaises(ControllerError):
            controller.execute({"state": "on"})
        self.assertEqual(controller.observe().available, False)

    def test_restart_is_detected_and_nothing_is_replayed(self):
        controller, _, esp = _controller()
        controller.execute({"state": "on"})
        first_boot = controller.boot_id
        esp.reboot()  # comes up dark, new boot id, no pending command
        observed = controller.observe()
        self.assertEqual((observed.available, observed.state), (True, "off"))
        self.assertNotEqual(controller.boot_id, first_boot)
        self.assertEqual(controller.restarts, 1)
        # The readback resynchronized state; it did not re-send the earlier ON.
        self.assertEqual((esp.state, esp.commands), ("off", 1))

    def test_concurrent_exchanges_do_not_consume_each_other(self):
        controller, _, esp = _controller(timeout=2.0)
        results, errors = [], []

        def drive(state):
            try:
                results.append(controller.execute({"state": state}))
            except Exception as exc:  # pragma: no cover - failure detail only
                errors.append(exc)

        threads = [threading.Thread(target=drive, args=(s,))
                   for s in ("on", "off", "on", "off")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 4)
        self.assertTrue(all(r.accepted for r in results))
        self.assertEqual(esp.commands, 4)


class TransportSelectionTest(unittest.TestCase):
    """Exactly one transport, never a silent fallback."""

    def test_requires_exactly_one_transport(self):
        with self.assertRaises(StartupError):
            _make_controller(None, None, 115200, 2.0)
        with self.assertRaises(StartupError):
            _make_controller("http://127.0.0.1:1", "/dev/ttyACM0", 115200, 2.0)

    def test_each_transport_selects_its_own_controller(self):
        serial_controller = _make_controller(None, "/dev/ttyACM0", 115200, 2.0)
        self.assertIsInstance(serial_controller, SerialLightController)
        http_controller = _make_controller("http://127.0.0.1:1", None, 115200, 2.0)
        self.assertNotIsInstance(http_controller, SerialLightController)

    def test_importing_the_runtime_does_not_require_pyserial(self):
        # The serial dependency stays optional for every HTTP-only user.
        code = ("import sys; import dcamr.main; "
                "assert 'serial' not in sys.modules, sorted(sys.modules)")
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True,
                       capture_output=True)


class SerialRuntimeTest(unittest.TestCase):
    """The authorized pipeline driving the serial controller end to end."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="alice-serial-light-")
        root = Path(cls._tmp.name)
        cls.release_dir = build_release.build(root / "bundle")
        cls.trusted = bytes.fromhex(
            (root / "bundle" / "trust" / "manifest_public.hex").read_text().strip())
        cls.seed = bytes.fromhex(
            (root / "bundle" / "client" / "term-agent-01-k1.seed").read_text().strip())
        cls.runtime = FirstLightRuntime(
            release_dir=cls.release_dir, trusted_manifest_key=cls.trusted,
            data_dir=root / "pi-data", esp_base_url="http://127.0.0.1:1")
        # Swap in the serial transport over the simulator; self.controller is a
        # public seam and the runtime cannot tell the two transports apart.
        transport, cls.esp = mock_esp_serial.make_loopback()
        cls.runtime.controller = SerialLightController(
            "loopback", timeout=0.5, transport=transport)

    @classmethod
    def tearDownClass(cls):
        cls.runtime.close()
        cls._tmp.cleanup()

    def test_authorized_request_drives_the_serial_light(self):
        envelope = build_envelope(self.seed, state="on")
        code, payload = self.runtime.handle_request(envelope)
        self.assertEqual((code, payload["decision"]), (200, "ALLOW"))
        self.assertEqual(payload["execution"], "COMPLETED")
        self.assertEqual(payload["observed_state"], "on")
        self.assertEqual(self.esp.state, "on")

    def test_denied_request_sends_no_command(self):
        before = self.esp.commands
        bad = build_envelope(self.seed, state="on", agent_id="other-agent")
        code, payload = self.runtime.handle_request(bad)
        self.assertNotEqual(payload["decision"], "ALLOW")
        # A refused request leaves the LED exactly as it was.
        self.assertEqual(self.esp.commands, before)

    def test_repeated_signed_request_writes_once(self):
        envelope = build_envelope(self.seed, state="off")
        before = self.esp.commands
        code, first = self.runtime.handle_request(envelope)
        self.assertEqual(code, 200)
        code, second = self.runtime.handle_request(envelope)
        self.assertEqual(code, 200)
        self.assertTrue(second.pop("idempotent_replay"))
        self.assertEqual(second, first)
        # Idempotency is the runtime's; the transport adds no dedup of its own.
        self.assertEqual(self.esp.commands, before + 1)

    def test_execution_attempt_is_durable_before_the_write(self):
        envelope = build_envelope(self.seed, state="on")
        request_id = envelope["request"]["request_id"]
        self.runtime.handle_request(envelope)
        events = list(self.runtime.iter_events(after=0))
        types = [e["event_type"] for e in events
                 if e["event_id"].startswith(request_id + ".")]
        self.assertIn("EXECUTION_ATTEMPT", types)
        attempt = types.index("EXECUTION_ATTEMPT")
        receipt = types.index("CONTROLLER_RECEIPT")
        self.assertLess(attempt, receipt)


@unittest.skipUnless(HAS_PYSERIAL, "install requirements-hardware.txt for the PTY serial test")
class SerialPtyTest(unittest.TestCase):
    """The same controller over a real serial.Serial on a pseudo-terminal."""

    def test_real_serial_framing_round_trip(self):
        primary, secondary = os.openpty()
        esp = mock_esp_serial.MockSerialEsp()
        stop = threading.Event()

        def device():
            buffer = b""
            while not stop.is_set():
                try:
                    chunk = os.read(primary, 256)
                except OSError:
                    return
                if not chunk:
                    return
                buffer += chunk
                while b"\n" in buffer:
                    line, _, buffer = buffer.partition(b"\n")
                    for out in esp.handle(line):
                        os.write(primary, out)

        thread = threading.Thread(target=device, daemon=True)
        thread.start()
        controller = SerialLightController(os.ttyname(secondary), timeout=2.0)
        try:
            receipt = controller.execute({"state": "on"})
            self.assertTrue(receipt.accepted)
            self.assertEqual(controller.observe().state, "on")
            self.assertEqual(esp.commands, 1)
        finally:
            controller.close()
            stop.set()
            os.close(secondary)
            os.close(primary)


if __name__ == "__main__":
    unittest.main()

class MultiLightReplyTest(unittest.TestCase):
    def test_wrong_channel_ack_is_not_accepted(self):
        class Wire:
            def write(self, data): return len(data)
        c = SerialLightController('test', transport=Wire())
        c._await_reply = lambda *_: {'v':2,'channel':3,'ok':True,'state':'on','boot_id':'00000001'}
        with self.assertRaises(ControllerError):
            c.execute_target('ESP-LIGHT-02', {'state':'on'})

    def test_unknown_target_never_opens_serial(self):
        c = SerialLightController('must-not-open')
        with self.assertRaises(ControllerError):
            c.execute_target('ESP-LIGHT-09', {'state':'on'})
