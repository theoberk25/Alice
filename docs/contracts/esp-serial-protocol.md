# ESP light node USB serial protocol

Updated: 2026-09-06. Wire contract between the Pi runtime
([serial_light_controller.py](../../dcamr/enforcement/serial_light_controller.py)) and
the XIAO ESP32-S3 light node
([xiao_first_light.ino](../../firmware/xiao_first_light/xiao_first_light.ino)).

Production supports eight mapped LEDs. Version 1 retains the original D0-only
messages; version 2 requires an integer channel from 1 through 8 on SET and GET.
Both success and rejection replies echo version/channel; the Pi rejects a reply
whose version or channel differs from its request. A command ID is correlation,
not authorization. See the [hardware mapping](../guides/first-light-hardware.md#verified-channel-map).

```json
{"v":2,"id":"example","channel":8,"op":"set","state":"on"}
{"v":2,"id":"example","channel":8,"ok":true,"state":"on","boot_id":"41de7829"}
```

Version 1 rejects any channel field; version 2 rejects missing/out-of-range channels.
Only the selected output changes. Every output starts LOW. The signed request
carries target ESP-LIGHT-01..08; the runtime maps it to the fixed channel, never
to a client-selected raw GPIO. Existing framing, duplicate-field, deadline and
no-uncertain-retry rules below apply to both versions.

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
| `v` | Protocol version; `1` (D0) or `2` (explicit channel). Other values are `BAD_VERSION`. |
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

The current eight-LED bench wiring is recorded in the [hardware runbook](../guides/first-light-hardware.md#verified-channel-map).
Production firmware starts all eight outputs LOW; signed grants determine which
channel requests can execute.

## Slow-blink display behavior

ON now enables a nonblocking 1-second HIGH / 1-second LOW cycle, starting HIGH.
OFF disables blinking and drives LOW immediately. GET state describes the logical
blink-enabled state, not the instantaneous GPIO phase or measured illumination.
Each channel has its own timer; no recurring Pi requests or audit events are
generated by the display cycle. Other channels and serial handling remain active.

## Version 3 environmental patterns

V1/V2 remain unchanged, including legacy ON's 1-second HIGH / 1-second LOW cycle.
V3 is telemetry display control, never fan authorization. It uses the same framing,
strict parsing, ID matching, single serial owner and configured-output readback.

```json
{"v":3,"id":"p1","channel":2,"op":"pattern","mode":"blink","mhz":4550}
{"v":3,"id":"p1","channel":2,"ok":true,"mode":"blink","mhz":4550,"stale":false,"boot_id":"00000001"}
{"v":3,"id":"p2","channel":2,"op":"get"}
{"v":3,"id":"p3","channel":2,"op":"keep"}
```

`mhz` is integer millihertz: 500–5000 for BLINK, exactly 0 otherwise. Modes are
`off`, `solid`, `blink`, `unavailable`. GET may also return `legacy`. Pattern writes
require both mode and rate; GET/KEEP reject them. `state` is invalid in V3. Invalid
settings return BAD_PATTERN and leave configuration untouched. Success readback
reports mode/rate/staleness, never an instantaneous edge or measured illumination.

A pattern or keep for channels 1/5, 2/6, 3/7 addresses the entire same-color pair
atomically. Channels 4 and 8 remain independent. Repeated settings and rate changes
preserve full-cycle phase; pairs share phase. A 5 ms monotonic polling scheduler
uses elapsed-time accumulation with uint32 rollover handling, not chained sleeps.
BLINK duty is 50%. MCU/USB hardware timing still needs physical acceptance.

Pattern/KEEP refresh a fixed 2000 ms lease. Expiry switches to UNAVAILABLE with
`stale:true`; KEEP cannot revive it. Explicit new telemetry settings are needed.
UNAVAILABLE physically emits two 75 ms pulses separated by 75 ms every 2 seconds,
synchronized across unavailable channels, distinctly different from normal rates
and OFF. Explicit unavailable mode has `stale:false` until its own lease expires.
GET never renews a lease. The host marks source data older than 1 second unavailable
and keeps unchanged live configurations alive every 500 ms per group.

Latest explicit SET wins on its addressed channel: V1/V2 SET cancels V3 there,
retaining legacy semantics; a subsequent V3 pattern replaces both members of a
non-white pair. GET/KEEP never override legacy control. Demo operation provides no
legacy write API and uses the one shared controller; do not run a second service
on the port. Reset starts OFF/legacy without replay. The renderer notices boot
changes and reconciles uncertain writes with GET before delivering a later fresh
snapshot. No automatic replay of uncertain signed actions is introduced.
