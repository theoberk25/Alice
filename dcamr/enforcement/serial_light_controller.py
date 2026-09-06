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


def _decode(raw: bytes):
    """Return a well-formed reply dict, or None if the line is unusable."""
    try:
        reply = json.loads(raw.decode("ascii").strip())
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(reply, dict) or reply.get("v") != PROTOCOL_VERSION:
        return None
    if not isinstance(reply.get("id"), str) or not isinstance(reply.get("ok"), bool):
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
        try:
            transport.write(line)
            flush = getattr(transport, "flush", None)
            if flush is not None:
                flush()
        except Exception as exc:
            self._drop()
            raise ControllerError("serial write failed") from exc
        return self._await_reply(transport, command_id)

    def _await_reply(self, transport, command_id: str) -> dict:
        deadline = time.monotonic() + self._timeout
        while True:
            if time.monotonic() >= deadline:
                # The command may or may not have been applied. Callers must
                # treat this as unknown, never as failure-to-execute.
                raise ControllerError("no acknowledgment before the deadline")
            try:
                raw = transport.readline()
            except Exception as exc:
                self._drop()
                raise ControllerError("serial read failed") from exc
            if not raw:
                time.sleep(0.005)
                continue
            if len(raw) > MAX_LINE_BYTES or not raw.endswith(b"\n"):
                # Oversized or partial: drop it and resynchronize at the next
                # newline rather than parsing a fragment.
                continue
            reply = _decode(raw)
            if reply is None or reply.get("id") != command_id:
                # Malformed or stale (an answer to some earlier command). Never
                # accepted as ours.
                continue
            self._note_boot(reply.get("boot_id"))
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
