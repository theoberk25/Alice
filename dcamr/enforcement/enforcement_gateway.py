"""Minimal ESP light controller transport for the first-light test.

Stdlib-only HTTP client. A receipt is a transport acknowledgement only, and the
observed state is read back separately; neither is an execution authority, and
idempotency is owned by the runtime, not this transport. The real ESP firmware
contract is an open coordination item; until it lands, callers point this at
lab.first_light.mock_esp. Placement per AGENTS.md (Pi runtime stays in dcamr/).
"""

from dataclasses import dataclass
import json
from urllib import error, request as urlrequest


class ControllerError(RuntimeError):
    """Transport failed; the outcome at the device is unknown."""


@dataclass(frozen=True)
class ControllerReceipt:
    accepted: bool
    status_code: int | None
    body: dict


@dataclass(frozen=True)
class ObservedState:
    available: bool
    state: str | None


class LightController:
    """Open contract: POST {base}/light {"state": ...}; GET {base}/light."""

    def __init__(self, base_url: str, timeout: float = 3.0):
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def execute(self, parameters: dict) -> ControllerReceipt:
        body = json.dumps({"state": parameters["state"]}).encode("utf-8")
        req = urlrequest.Request(self._base + "/light", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
        try:
            with urlrequest.urlopen(req, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return ControllerReceipt(True, response.status, payload)
        except error.HTTPError as exc:
            return ControllerReceipt(False, exc.code, {})
        except (OSError, ValueError) as exc:
            raise ControllerError("light controller unreachable") from exc

    def observe(self) -> ObservedState:
        try:
            with urlrequest.urlopen(self._base + "/light", timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                state = payload.get("state")
                return ObservedState(state in ("on", "off"), state if state in ("on", "off") else None)
        except (OSError, ValueError):
            return ObservedState(False, None)
