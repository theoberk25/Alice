"""Stdlib simulator of the XIAO ESP32-S3 serial light node, for tests.

Mirrors mock_esp.py for the USB transport: the same validation rules the
firmware applies (version, operation, field types, exact state values, unknown
fields, framing limit), a `commands` counter so tests can prove idempotent
retries send exactly one device write, and a `boot_id` that changes on reboot().

The fault switches (drop_next, wrong_id_next, wrong_state_next, malformed_next,
reject_next) exist so the Pi controller's failure paths can be exercised without
hardware. Placement per AGENTS.md: lab tooling lives in scripts/lab/.
"""

import json
import uuid

PROTOCOL_VERSION = 1
MAX_LINE_BYTES = 256
STATES = ("on", "off")
SET_FIELDS = {"v", "id", "op", "state"}
GET_FIELDS = {"v", "id", "op"}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _boot_id():
    return uuid.uuid4().hex[:8]


class MockSerialEsp:
    """Device-side state and the exact firmware validation rules."""

    def __init__(self):
        self.state = "off"
        self.commands = 0
        self.boot_id = _boot_id()
        # One-shot fault injection; each is a count of replies to affect.
        self.drop_next = 0
        self.wrong_id_next = 0
        self.wrong_state_next = 0
        self.malformed_next = 0
        self.reject_next = 0

    def reboot(self):
        """Power-cycle semantics: dark, new boot id, nothing replayed."""
        self.state = "off"
        self.boot_id = _boot_id()

    def _ok(self, command_id):
        state = self.state
        if self.wrong_state_next > 0:
            self.wrong_state_next -= 1
            state = "off" if state == "on" else "on"
        return {"v": PROTOCOL_VERSION, "id": command_id, "ok": True,
                "state": state, "boot_id": self.boot_id}

    def _error(self, command_id, code):
        return {"v": PROTOCOL_VERSION, "id": command_id, "ok": False,
                "error": code, "boot_id": self.boot_id}

    def handle(self, line: bytes) -> list:
        """Return the reply lines for one received frame (possibly none)."""
        reply, applied = self._evaluate(line)
        if applied:
            self.commands += 1
        out = []
        if self.malformed_next > 0:
            self.malformed_next -= 1
            out.append(b"{not json\n")
        if self.drop_next > 0:
            self.drop_next -= 1
            return out
        if self.wrong_id_next > 0:
            self.wrong_id_next -= 1
            reply = dict(reply, id="stale-" + uuid.uuid4().hex[:8])
        out.append(json.dumps(reply, separators=(",", ":")).encode("ascii") + b"\n")
        return out

    def _evaluate(self, line: bytes):
        """Validate one frame. Returns (reply, applied_to_gpio)."""
        if len(line) + 1 > MAX_LINE_BYTES:
            return self._error("", "LINE_TOO_LONG"), False
        try:
            message = json.loads(line.decode("ascii"), object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, ValueError):
            return self._error("", "MALFORMED"), False
        if not isinstance(message, dict):
            return self._error("", "MALFORMED"), False

        command_id = message.get("id")
        if not isinstance(command_id, str) or not command_id or len(command_id) > 32:
            return self._error("", "MALFORMED"), False
        if type(message.get("v")) is not int or message["v"] != PROTOCOL_VERSION:
            return self._error(command_id, "BAD_VERSION"), False

        op = message.get("op")
        if op is None:
            return self._error(command_id, "MISSING_FIELD"), False
        if op not in ("set", "get"):
            return self._error(command_id, "BAD_OP"), False

        allowed = SET_FIELDS if op == "set" else GET_FIELDS
        if set(message) - allowed:
            return self._error(command_id, "UNKNOWN_FIELD"), False

        if op == "get":
            # Readback never touches the output.
            return self._ok(command_id), False

        state = message.get("state")
        if state not in STATES:
            return self._error(command_id, "BAD_STATE"), False
        if self.reject_next > 0:
            self.reject_next -= 1
            # Device-side refusal: reached and declined, output unchanged.
            return self._error(command_id, "INVALID_COMMAND"), False
        self.state = state
        return self._ok(command_id), True


class LoopbackTransport:
    """In-process stand-in for serial.Serial (write/read/readline/close).

    Accumulates partial writes until a newline, so tests can split a command
    across several write() calls exactly as a real link would.
    """

    def __init__(self, esp: MockSerialEsp):
        self._esp = esp
        self._rx = bytearray()
        self._pending = bytearray()
        self.closed = False
        self.offline = False

    def write(self, data: bytes) -> int:
        if self.offline or self.closed:
            raise OSError("serial device disconnected")
        self._pending.extend(data)
        while b"\n" in self._pending:
            line, _, rest = bytes(self._pending).partition(b"\n")
            self._pending = bytearray(rest)
            for out in self._esp.handle(line):
                self._rx.extend(out)
        return len(data)

    def read(self, size=1) -> bytes:
        if self.closed:
            raise OSError("serial device closed")
        if self.offline:
            return b""
        chunk = bytes(self._rx[:size])
        del self._rx[:size]
        return chunk

    def readline(self) -> bytes:
        if self.closed:
            raise OSError("serial device closed")
        if self.offline:
            return b""
        index = self._rx.find(b"\n")
        if index < 0:
            # No complete frame available: hand back whatever is buffered, the
            # way a real readline() returns a partial line at its timeout.
            partial = bytes(self._rx)
            self._rx.clear()
            return partial
        line = bytes(self._rx[:index + 1])
        del self._rx[:index + 1]
        return line

    def feed(self, raw: bytes):
        """Inject unsolicited bytes, e.g. a stale reply or a torn frame."""
        self._rx.extend(raw)

    def close(self):
        self.closed = True


def make_loopback():
    """Return (transport, esp), mirroring mock_esp.make_server()."""
    esp = MockSerialEsp()
    return LoopbackTransport(esp), esp
