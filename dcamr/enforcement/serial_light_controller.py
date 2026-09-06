"""Direct USB-serial transport to the first-light XIAO ESP32-S3 light node.

Sibling of the HTTP LightController in enforcement_gateway.py and deliberately
interchangeable with it: the same execute(parameters)/observe() shapes and the
same ControllerReceipt/ObservedState/ControllerError semantics, so the runtime
does not learn which transport it holds. The Pi stays the authorization
authority; this module only frames commands, matches replies and reports what
the device acknowledged.

Deliberate non-behaviors, per the serial protocol contract: no retry of a SET
after an uncertain acknowledgment, no replay of a pending write on reconnect,
and no dedup of its own (idempotency is owned by the runtime). A command id is
correlation only, never authentication. pyserial is imported lazily so the HTTP
path and its tests keep working with no serial dependency installed. Placement
per AGENTS.md: Pi runtime modules live in dcamr/.
"""

import json
import math
import re
import threading
import time
import uuid

from dcamr.enforcement.enforcement_gateway import (ControllerError, ControllerReceipt,
                                                   ObservedState)

PROTOCOL_VERSION = 1
# Framing limit shared with the firmware; a longer line is discarded on both
# sides rather than parsed, so oversized input cannot exhaust memory.
MAX_LINE_BYTES = 256
STATES = ("on", "off")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate reply field")
        result[key] = value
    return result


def _decode(raw: bytes):
    """Return a well-formed reply dict, or None if the line is unusable."""
    try:
        reply = json.loads(raw.decode("ascii").strip(), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, ValueError):
        return None
    if (not isinstance(reply, dict) or type(reply.get("v")) is not int
            or reply["v"] not in (1, 2, 3)):
        return None
    if not isinstance(reply.get("id"), str) or not isinstance(reply.get("ok"), bool):
        return None
    if not isinstance(reply.get("boot_id"), str) or not re.fullmatch(r"[0-9a-f]{8}", reply["boot_id"]):
        return None
    expected = {"v", "id", "ok", "boot_id", "state" if reply["ok"] else "error"}
    if reply["v"] >= 2:
        expected.add("channel")
        if type(reply.get("channel")) is not int or not 1 <= reply["channel"] <= 8:
            return None
    if reply["v"] == 3 and reply["ok"]:
        expected.remove("state")
        expected.update(("mode", "mhz", "stale"))
        if (reply.get("mode") not in ("legacy", "off", "solid", "blink", "unavailable")
                or type(reply.get("mhz")) is not int or type(reply.get("stale")) is not bool
                or (reply["mode"] == "blink" and not 500 <= reply["mhz"] <= 5000)
                or (reply["mode"] != "blink" and reply["mhz"] != 0)):
            return None
    if set(reply) != expected:
        return None
    return reply


class SerialLightController:
    """Newline-delimited JSON over one explicitly named USB CDC device.

    Contract: {"v":1,"id":..,"op":"set","state":"on"|"off"} and
    {"v":1,"id":..,"op":"get"}; the node answers with ok/state/boot_id. See
    docs/contracts/esp-serial-protocol.md.
    """

    def __init__(self, device: str, *, baud: int = 115200, timeout: float = 2.0,
                 transport=None):
        if (type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0 < timeout <= 10):
            raise ValueError("Serial timeout must be finite and in (0, 10] seconds")
        self._discarding = False
        self._device = device
        self._baud = baud
        self._timeout = timeout
        self._lock = threading.Lock()
        self._transport = transport
        # An injected transport belongs to the caller: never reopened, never
        # closed underneath them. Only a port we opened is ours to manage.
        self._owns_transport = transport is None
        self._boot_id = None
        self.restarts = 0

    @property
    def boot_id(self):
        """Last boot id reported by the node, or None before the first reply."""
        return self._boot_id

    # ------------------------------------------------------------- transport
    def _open(self):
        if self._transport is not None:
            return self._transport
        try:
            import serial  # optional; see requirements-hardware.txt
        except ImportError as exc:
            raise ControllerError("pyserial is not installed") from exc
        try:
            port = serial.Serial()
            port.port = self._device
            port.exclusive = True  # cooperating POSIX serial owners cannot overlap
            port.baudrate = self._baud
            port.timeout = self._timeout
            port.write_timeout = self._timeout
            # Asserting DTR/RTS on open resets the XIAO; set both low first so
            # attaching the runtime never power-cycles the light.
            port.dtr = False
            port.rts = False
            port.open()
        except Exception as exc:
            raise ControllerError(f"serial device unavailable: {self._device}") from exc
        self._transport = port
        return port

    def _drop(self):
        """Forget a broken port so the next command reopens it.

        Reopening is a fresh connection for a *new* command; the failed write is
        never resent.
        """
        if not self._owns_transport:
            return
        self._discarding = False
        transport, self._transport = self._transport, None
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass

    def close(self):
        with self._lock:
            self._drop()

    # -------------------------------------------------------------- exchange
    def _note_boot(self, boot_id):
        if not isinstance(boot_id, str) or not boot_id:
            return
        if self._boot_id is not None and boot_id != self._boot_id:
            # The node restarted. It came up dark and holds no pending command;
            # this only marks earlier readings stale, it never re-sends.
            self.restarts += 1
        self._boot_id = boot_id

    def _exchange(self, payload: dict) -> dict:
        command_id = uuid.uuid4().hex[:16]
        message = {"v": PROTOCOL_VERSION, "id": command_id}
        message.update(payload)
        line = json.dumps(message, separators=(",", ":")).encode("ascii") + b"\n"
        if len(line) > MAX_LINE_BYTES:
            raise ControllerError("command exceeds the framing limit")

        transport = self._open()
        deadline = time.monotonic() + self._timeout
        try:
            if transport.write(line) != len(line):
                raise OSError("partial serial write")
            # Serial.write already has write_timeout. POSIX flush/tcdrain has
            # no bounded timeout and could stall the shared runtime owner lock.
        except Exception as exc:
            self._drop()
            raise ControllerError("serial write failed") from exc
        reply = self._await_reply(transport, command_id, deadline)
        if reply['v'] != message['v'] or (message['v'] >= 2 and reply.get('channel') != message['channel']):
            raise ControllerError("reply channel/version mismatch")
        return reply

    def _await_reply(self, transport, command_id: str, deadline: float) -> dict:
        buffer = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._discarding = self._discarding or bool(buffer)
                raise ControllerError("no acknowledgment before the deadline")
            try:
                # readline's timeout is per underlying read, so a continuous
                # stream can evade it. Read one byte under the absolute deadline.
                if hasattr(transport, "timeout"):
                    transport.timeout = remaining
                raw = transport.read(1)
            except Exception as exc:
                self._drop()
                raise ControllerError("serial read failed") from exc
            if time.monotonic() >= deadline:
                self._discarding = (False if raw == b"\n" else
                                    self._discarding or bool(buffer) or bool(raw))
                raise ControllerError("no acknowledgment before the deadline")
            if not raw:
                time.sleep(min(.005, max(0, deadline - time.monotonic())))
                continue
            if self._discarding:
                if raw == b"\n":
                    self._discarding = False
                continue
            if raw != b"\n":
                buffer.extend(raw)
                if len(buffer) >= MAX_LINE_BYTES:
                    buffer.clear()
                    self._discarding = True
                continue
            reply = _decode(bytes(buffer))
            buffer.clear()
            if reply is None or reply.get("id") != command_id:
                continue
            self._note_boot(reply["boot_id"])
            return reply

    # ---------------------------------------------------------------- public
    def execute(self, parameters: dict) -> ControllerReceipt:
        state = parameters["state"]
        if state not in STATES:
            # Unreachable through the signed schema; refuse without writing.
            raise ControllerError(f"unsupported light state: {state!r}")
        with self._lock:
            reply = self._exchange({"op": "set", "state": state})
        if not reply["ok"]:
            # The device answered and refused: reached, not unknown.
            return ControllerReceipt(False, None, reply)
        if reply.get("state") != state:
            # A contradictory acknowledgment is a rejection, not a success.
            return ControllerReceipt(False, None, reply)
        return ControllerReceipt(True, None, reply)

    def observe(self) -> ObservedState:
        """Separate readback. Never raises; never returns a cached write.

        This is the node's own reported output state, not measured illumination.
        """
        try:
            with self._lock:
                reply = self._exchange({"op": "get"})
        except Exception:
            return ObservedState(False, None)
        if not reply["ok"]:
            return ObservedState(False, None)
        state = reply.get("state")
        if state not in STATES:
            return ObservedState(False, None)
        return ObservedState(True, state)

    def execute_target(self, target, parameters):
        channel = self._channel(target)
        if channel == 1:
            return self.execute(parameters)
        state = parameters.get("state")
        if state not in STATES:
            raise ControllerError("unsupported light state")
        with self._lock:
            reply = self._exchange({"v": 2, "channel": channel, "op": "set", "state": state})
        return ControllerReceipt(reply["ok"] and reply.get("state") == state, None, reply)

    def observe_target(self, target):
        channel = self._channel(target)
        if channel == 1:
            return self.observe()
        try:
            with self._lock:
                reply = self._exchange({"v": 2, "channel": channel, "op": "get"})
            state = reply.get("state")
            return ObservedState(reply["ok"] and state in STATES, state if reply["ok"] and state in STATES else None)
        except ControllerError:
            return ObservedState(False, None)

    def pattern(self, channel, *, mode=None, mhz=0, operation="pattern"):
        """v3 settings/readback through the same locked serial owner; no retries."""
        if type(channel) is not int or not 1 <= channel <= 8:
            raise ControllerError("unknown pattern channel")
        payload = {"v": 3, "channel": channel, "op": operation}
        if operation == "pattern":
            if (mode not in ("off", "solid", "blink", "unavailable") or type(mhz) is not int
                    or (mode == "blink" and not 500 <= mhz <= 5000)
                    or (mode != "blink" and mhz != 0)):
                raise ControllerError("invalid pattern")
            payload.update(mode=mode, mhz=mhz)
        elif operation not in ("get", "keep"):
            raise ControllerError("invalid pattern operation")
        with self._lock:
            reply = self._exchange(payload)
        if not reply["ok"]:
            raise ControllerError("pattern rejected by firmware")
        if operation == "pattern" and (reply["mode"] != mode or reply["mhz"] != mhz or reply["stale"]):
            raise ControllerError("pattern acknowledgment mismatch")
        return reply

    @staticmethod
    def _channel(target):
        targets = [f"ESP-LIGHT-{i:02d}" for i in range(1, 9)]
        if target not in targets:
            raise ControllerError("unknown light target")
        return targets.index(target) + 1
