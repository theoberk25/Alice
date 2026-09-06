# ESP light node USB serial protocol

Updated: 2026-09-06. Wire contract between the Pi runtime
([serial_light_controller.py](../../dcamr/enforcement/serial_light_controller.py)) and
the XIAO ESP32-S3 light node
([xiao_first_light.ino](../../firmware/xiao_first_light/xiao_first_light.ino)).

This contract covers **one light and one transport**. It does not widen the signed
[action request schema](../../common/schemas/action_request.json), which still permits
exactly `set_light_state` on `ESP-LIGHT-01` with `{"state":"on"|"off"}`. A command id
is correlation only and carries no authority: the node trusts whichever host owns its
USB port, so this is no defense against a compromised Pi. Setup steps are in the
[hardware runbook](../guides/first-light-hardware.md).

## System authority

The Pi authenticates, resolves permissions, decides and records the durable audit
trail before anything reaches the node. The node holds no policy, no network and no
decisions; it applies an output and reports what it applied. An acknowledgment is a
transport receipt, not proof of authorization, and never an authority to execute.

## Transport

Newline-delimited JSON (UTF-8/ASCII) over native USB CDC at 115200 baud, 8N1.
Both sides cap a frame at **256 bytes including the newline** and discard anything
longer, resynchronizing at the next newline. Neither side emits debug prose on this
stream. The Pi opens the port with DTR and RTS held low, because asserting either
resets the board.

## Messages

Pi to node:

```json
{"v":1,"id":"3e215777cf944f18","op":"set","state":"on"}
{"v":1,"id":"b0dfa8d01dcb484a","op":"set","state":"off"}
{"v":1,"id":"9c0f11ab77de4c02","op":"get"}
```

Node to Pi:

```json
{"v":1,"id":"3e215777cf944f18","ok":true,"state":"on","boot_id":"41de7829"}
{"v":1,"id":"3e215777cf944f18","ok":false,"error":"BAD_STATE","boot_id":"41de7829"}
```

| Field | Meaning |
| --- | --- |
| `v` | Protocol version; currently `1`. Any other value is `BAD_VERSION`. |
| `id` | Per-exchange correlation token, 1-32 characters. Distinct from the signed `request_id` and never reused across commands. |
| `op` | `set` or `get`. `set` requires `state`; `get` must not carry one. |
| `state` | Exactly `"on"` or `"off"`. On a reply it is the node's own driven output. |
| `ok` | Whether the node accepted and applied the frame. |
| `error` | Present when `ok` is false. |
| `boot_id` | 8 hex characters, regenerated every boot so restarts and stale replies are detectable. |

Error codes: `BAD_VERSION`, `BAD_OP`, `BAD_STATE`, `UNKNOWN_FIELD`, `MISSING_FIELD`,
`LINE_TOO_LONG`, `MALFORMED`.

## Rules the schema alone does not express

- **`set` is explicit.** There is no toggle, and `get` never alters the output.
- **Any rejected frame leaves GPIO untouched**, including unknown or duplicated
  fields, a bad version, and oversized input.
- **The node applies the output before acknowledging**, so an acknowledgment always
  follows a real write.
- **A reply is only ours when `id` matches.** Mismatched ids are stale and discarded,
  never accepted as the answer to the current command.
- **For `set`, the acknowledged `state` must equal the requested state.** A
  contradictory acknowledgment is a rejection, not a success.
- **Reset comes up OFF.** No pending command is stored or replayed at boot, and a
  host disconnect or timeout never implicitly changes the light.
- **Uncertainty is preserved.** A timeout or dropped acknowledgment means the command
  may or may not have been applied; the Pi records UNKNOWN and never auto-retries a
  `set` or replays a failed write on reconnect. A later `get` resynchronizes state but
  does not retroactively prove an earlier uncertain command executed.
- **Idempotency belongs to the runtime**, which replays a recorded outcome for a
  repeated signed request. The transport adds no deduplication of its own.

## Outcome mapping

The controller reuses the existing
[gateway types](../../dcamr/enforcement/enforcement_gateway.py) so the runtime cannot
tell the two transports apart. `status_code` is always `null` on serial; no HTTP codes
are fabricated.

| Condition | Result | Runtime outcome |
| --- | --- | --- |
| `ok:true` and state matches | `ControllerReceipt(accepted=True)` | ACCEPTED / COMPLETED |
| `ok:false` | `ControllerReceipt(accepted=False)` | REJECTED / FAILED |
| `ok:true` with the wrong state | `ControllerReceipt(accepted=False)` | REJECTED / FAILED |
| port unavailable, write fails | `ControllerError` | UNKNOWN / UNKNOWN |
| no matching reply before the deadline | `ControllerError` | UNKNOWN / UNKNOWN |
| only malformed or stale lines | `ControllerError` | UNKNOWN / UNKNOWN |

`observe()` never raises; any failure reports `ObservedState(available=False)`.

## Limits

`state` is the node's **own reported output**, recorded as `ACTUATOR_FEEDBACK`. It is
not measured illumination and does not prove the LED lit — a failed lamp, a broken
resistor or miswiring all still report `on`. An independent sensor would be a separate
contract.

Exactly-once physical execution is **not** claimed across arbitrary crashes or lost
acknowledgments. The tested guarantee is narrower: one signed request produces at most
one device write, and an unprovable outcome is recorded as UNKNOWN rather than guessed.

Extending to multiple lights means adding a channel field here **and** widening the
signed action/target enums, which AGENTS.md treats as a coordinated contract change.

## Integration hardening

The host uses bounded byte reads under one write/reply deadline; timeout must be
finite and in `(0, 10]` seconds. It avoids unbounded `flush()` and `readline()` while
the runtime holds its owner lock, retains the 256-byte frame bound, and discards
oversized/partial frames through their next newline. Replies require an exact
integer version, unique fields and the declared eight-hex boot identity before a
matching acknowledgement can be accepted. No uncertain SET is retried.

Firmware now rejects leading-zero numeric versions, raw control characters in
strings and embedded NUL/trailing data before changing GPIO, and counts the newline
inside its 256-byte limit. Host-compiled tests exercise the actual firmware loop
against test-only serial/GPIO stubs. They do not establish Arduino board compilation
or physical acceptance of the changed firmware.
