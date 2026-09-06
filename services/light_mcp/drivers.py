"""Hardware driver seam for the Light-Control MCP server.

The server never talks to hardware directly; it talks to a ``LightDriver``.
Ship ``MockDriver`` now (in-memory + logs); drop in ``SerialDriver`` later with
zero change to the server or either agent. Selection is via ``LIGHT_DRIVER``.

The driver is the single source of truth for machine state — the server holds
no second copy.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urlerror, request as urlrequest

log = logging.getLogger("light_mcp.driver")


class LightDriver(ABC):
    """Abstract control surface for the machine indicator lights."""

    @abstractmethod
    def set(self, machine_id: str, state: str) -> None:
        """Drive ``machine_id`` to ``state``."""

    @abstractmethod
    def get_all(self) -> dict[str, str]:
        """Return a snapshot mapping of ``machine_id -> state``."""

    @abstractmethod
    def blink(self, machine_id: str, count: int, interval_ms: int) -> None:
        """Blink ``machine_id`` ``count`` times, restoring the prior state."""


class MockDriver(LightDriver):
    """In-memory driver. Logs every call; requires no hardware.

    Fully demoable today — swapping to ``SerialDriver`` later is invisible to
    the MCP server and to both agents.
    """

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._state: dict[str, str] = dict(initial or {})
        log.info("MockDriver init: %d machines %s", len(self._state), self._state)

    def set(self, machine_id: str, state: str) -> None:
        self._state[machine_id] = state
        log.info("MockDriver.set %s -> %s", machine_id, state)

    def get_all(self) -> dict[str, str]:
        return dict(self._state)

    def blink(self, machine_id: str, count: int, interval_ms: int) -> None:
        prior = self._state.get(machine_id)
        delay = max(0, interval_ms) / 1000.0
        log.info(
            "MockDriver.blink %s count=%s interval_ms=%s (prior=%s)",
            machine_id, count, interval_ms, prior,
        )
        for cycle in range(max(0, count)):
            self._state[machine_id] = "on"
            log.info("MockDriver.blink %s cycle %d -> on", machine_id, cycle + 1)
            time.sleep(delay)
            self._state[machine_id] = "off"
            log.info("MockDriver.blink %s cycle %d -> off", machine_id, cycle + 1)
            time.sleep(delay)
        if prior is not None:
            self._state[machine_id] = prior
        log.info("MockDriver.blink %s done, restored to %s", machine_id, self._state.get(machine_id))


# Stable signed light targets exposed by the enforcement controller (Jared's
# eight-light mapping, docs/integration/esp-handoff.md). Channel order.
ESP_TARGETS = tuple(f"ESP-LIGHT-{i:02d}" for i in range(1, 9))


class EspSerialDriver(LightDriver):
    """Real light path: delegates to ``dcamr.enforcement.serial_light_controller``.

    Reuses the vetted, hardened ``SerialLightController`` (``execute_target`` /
    ``observe_target`` over newline-delimited JSON to the XIAO ESP32-S3) instead
    of re-implementing serial. Controls all eight signed targets
    (``ESP-LIGHT-01``..``ESP-LIGHT-08``); each configured machine maps to one
    target. States are ``on``/``off`` only; ``blink`` is not a device primitive,
    so it is composed as on/off toggles.

    Two caveats worth remembering:
    * **Locality.** The XIAO is USB-attached to the *Pi*, so this driver only
      reaches hardware when the MCP runs on the Pi with ``LIGHT_SERIAL_PORT`` set
      to the ``/dev/serial/by-id/...`` node. From a laptop there is no serial
      device and it fails closed.
    * **Authority.** Calling the controller straight from the MCP bypasses the
      ALICE gate (identity / permissions / ML / enforcement / audit), which the
      ESP handoff explicitly warns against for governance. The gate-faithful path
      submits signed ``set_light_state`` requests to the Pi runtime instead and
      lets the Enforcement gateway actuate. See docs/agent-build/03-light-mcp.md.
    """

    _STATES = ("on", "off")

    def __init__(self, device: str | None, targets: dict[str, str], *,
                 baud: int = 115200, timeout: float = 2.0) -> None:
        if not device:
            raise ValueError("LIGHT_SERIAL_PORT is required when LIGHT_DRIVER=esp")
        unknown = sorted({t for t in targets.values() if t not in ESP_TARGETS})
        if unknown:
            raise ValueError(f"unknown ESP target(s) {unknown}; valid: {list(ESP_TARGETS)}")
        # Lazy import: the mock path never needs pyserial or the dcamr runtime.
        from dcamr.enforcement.serial_light_controller import SerialLightController

        self._targets = dict(targets)  # machine_id -> ESP-LIGHT-0N
        self._ctl = SerialLightController(device, baud=baud, timeout=timeout)
        log.info("EspSerialDriver -> %s controls %d target(s): %s",
                 device, len(self._targets), self._targets)

    def _target(self, machine_id: str) -> str:
        try:
            return self._targets[machine_id]
        except KeyError:
            raise ValueError(
                f"unknown machine_id {machine_id!r}; known={list(self._targets)}"
            ) from None

    def set(self, machine_id: str, state: str) -> None:
        target = self._target(machine_id)
        if state not in self._STATES:
            raise ValueError(f"esp light supports {self._STATES}, not {state!r}")
        receipt = self._ctl.execute_target(target, {"state": state})
        if not receipt.accepted:
            raise RuntimeError(f"{target} did not accept state {state!r}: {receipt.body}")

    def get_all(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for machine_id, target in self._targets.items():
            obs = self._ctl.observe_target(target)
            out[machine_id] = obs.state if obs.available else "unknown"
        return out

    def blink(self, machine_id: str, count: int, interval_ms: int) -> None:
        target = self._target(machine_id)
        prior = self._ctl.observe_target(target).state
        delay = max(0, interval_ms) / 1000.0
        for _ in range(max(0, count)):
            self._ctl.execute_target(target, {"state": "on"})
            time.sleep(delay)
            self._ctl.execute_target(target, {"state": "off"})
            time.sleep(delay)
        if prior in self._STATES:
            self._ctl.execute_target(target, {"state": prior})


class PiRuntimeDriver(LightDriver):
    """Governed path: MCP tool -> signed request -> ALICE Pi runtime (POST /request).

    The MCP (and the agent) NEVER touch hardware or the serial controller. Each
    ``set`` becomes a signed ``set_light_state`` request that the Pi runtime
    validates (identity / exact grants / decision) and, on ALLOW, enforces to the
    light with its own audit + USB/Wazuh evidence. This is the gate-faithful path
    the ESP handoff requires ("do not bypass ALICE").

    Signing matches scripts/lab/first_light/terminal_client.py: Ed25519 over
    ``canonical_bytes(request)``, base64 signature, envelope
    ``{request, key_id, signature}`` with ``key_id = "<agent>-k1"``.

    Observation: the signed schema has no 'get' action, so ``get_all`` returns the
    last ``observed_state`` ALICE reported per light (``unknown`` until first
    command). ALICE's audit ledger is the durable truth, not this cache.
    """

    _STATES = ("on", "off")

    def __init__(self, url: str, agent_id: str, seed_hex: str, targets: dict[str, str],
                 *, timeout: float = 10.0) -> None:
        unknown = sorted({t for t in targets.values() if t not in ESP_TARGETS})
        if unknown:
            raise ValueError(f"unknown ESP target(s) {unknown}; valid: {list(ESP_TARGETS)}")
        # Lazy imports: only the governed path needs cryptography + dcamr audit.
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from dcamr.audit.event_contract import canonical_bytes

        self._url = url.rstrip("/")
        self._agent = agent_id
        self._key_id = f"{agent_id}-k1"
        self._sk = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex.strip()))
        self._canonical = canonical_bytes
        self._targets = dict(targets)
        self._timeout = timeout
        self._last = {mid: "unknown" for mid in targets}
        log.info("PiRuntimeDriver -> %s as agent %r controls %d target(s)",
                 self._url, agent_id, len(targets))

    def _target(self, machine_id: str) -> str:
        try:
            return self._targets[machine_id]
        except KeyError:
            raise ValueError(
                f"unknown machine_id {machine_id!r}; known={list(self._targets)}"
            ) from None

    def _submit(self, target: str, state: str) -> dict:
        request = {
            "schema_version": "1.0",
            "request_id": str(uuid.uuid4()),
            "agent_id": self._agent,
            "action": "set_light_state",
            "target": target,
            "parameters": {"state": state},
            "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        signature = base64.b64encode(self._sk.sign(self._canonical(request))).decode("ascii")
        envelope = {"request": request, "key_id": self._key_id, "signature": signature}
        body = json.dumps(envelope).encode("utf-8")
        req = urlrequest.Request(self._url + "/request", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
        try:
            with urlrequest.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urlerror.HTTPError as exc:
            try:
                return json.loads(exc.read().decode("utf-8"))
            except Exception:
                raise RuntimeError(f"ALICE runtime HTTP {exc.code}") from exc
        except urlerror.URLError as exc:
            raise RuntimeError(f"ALICE runtime unreachable at {self._url}: {exc.reason}") from exc

    def set(self, machine_id: str, state: str) -> None:
        target = self._target(machine_id)
        if state not in self._STATES:
            raise ValueError(f"light supports {self._STATES}, not {state!r}")
        payload = self._submit(target, state)
        observed = payload.get("observed_state")
        if observed in self._STATES:
            self._last[machine_id] = observed
        decision = payload.get("decision")
        execution = payload.get("execution")
        if not (decision == "ALLOW" and execution == "COMPLETED"):
            raise RuntimeError(
                f"ALICE {decision or 'no-decision'} "
                f"({payload.get('reason_code', 'no-reason')}); execution={execution}"
            )

    def get_all(self) -> dict[str, str]:
        return dict(self._last)

    def blink(self, machine_id: str, count: int, interval_ms: int) -> None:
        prior = self._last.get(machine_id)
        delay = max(0, interval_ms) / 1000.0
        for _ in range(max(0, count)):
            self.set(machine_id, "on")
            time.sleep(delay)
            self.set(machine_id, "off")
            time.sleep(delay)
        if prior in self._STATES:
            self.set(machine_id, prior)


def make_driver(
    kind: str,
    defaults: dict[str, str],
    *,
    serial_port: str | None = None,
    serial_baud: int = 115200,
    targets: dict[str, str] | None = None,
) -> LightDriver:
    """Instantiate a driver from ``LIGHT_DRIVER``:

    * ``mock`` — in-memory (default); no hardware, no ALICE.
    * ``esp``/``serial`` — DIRECT serial to the XIAO via the enforcement
      controller. Reaches hardware only when the MCP runs on the Pi, and BYPASSES
      the ALICE gate (bench use only).
    * ``alice``/``pi``/``governed`` — GATE-FAITHFUL: signs and POSTs each request
      to the Pi runtime, which decides / enforces / audits. Needs env
      ``ALICE_AGENT_ID``, ``ALICE_AGENT_KEY_FILE`` (hex seed) and
      ``ALICE_RUNTIME_URL``.
    """
    kind = (kind or "mock").lower()
    tmap = targets or {machine_id: machine_id for machine_id in defaults}
    if kind == "mock":
        return MockDriver(defaults)
    if kind in ("esp", "serial"):
        return EspSerialDriver(serial_port, tmap, baud=serial_baud)
    if kind in ("alice", "pi", "governed"):
        agent = os.environ.get("ALICE_AGENT_ID")
        key_file = os.environ.get("ALICE_AGENT_KEY_FILE")
        url = os.environ.get("ALICE_RUNTIME_URL", "http://127.0.0.1:18080")
        if not agent or not key_file:
            raise ValueError(
                "ALICE_AGENT_ID and ALICE_AGENT_KEY_FILE are required for the governed driver"
            )
        seed_hex = Path(key_file).expanduser().read_text()
        return PiRuntimeDriver(url, agent, seed_hex, tmap)
    raise ValueError(
        f"unknown LIGHT_DRIVER={kind!r} "
        "(expected 'mock', 'esp'/'serial', or 'alice'/'pi'/'governed')"
    )
