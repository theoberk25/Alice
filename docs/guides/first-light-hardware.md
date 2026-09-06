# First-light hardware runbook — XIAO ESP32-S3 over USB

Updated: 2026-09-06. Build, flash and run the one-LED light node that the Pi runtime
commands over USB serial. Read [AGENTS.md](../../AGENTS.md) and
[current.md](../../current.md) first; the wire contract is the
[serial protocol](../contracts/esp-serial-protocol.md).

## Scope and authority

One LED, one transport. The Pi authenticates, authorizes and records the audit trail;
the XIAO applies an output and reports it. The node has no network, no policy and no
decisions. Nothing here implements the technician approval (HOLD) flow, multiple
lights, sensors or motors.

## Wiring

Active HIGH, one circuit:

```
XIAO D0 (GPIO1) ──[ 270 Ω ]──▶│── LED ──┐
                            anode  cathode
                            (long)  (short)
                                        │
XIAO GND ───────────────────────────────┘
```

- **D0 is GPIO1.** Not GPIO0, and not the onboard user LED on GPIO21.
- Power comes from the Pi's USB port; the LED is the only load.
- **D6 (GPIO43) is the ROM UART0 TX pin and idles HIGH**, so anything wired there
  lights on its own before any code runs. The firmware claims that pin and holds it
  low at boot so the bench is unambiguous. This is pin hygiene, not a second
  controlled light. Removing those two lines in `setup()` restores UART0 TX if you
  need hardware-serial debugging.

## Build and upload

Requires `arduino-cli` with the `esp32:esp32` core (tested with core 3.3.11 and
arduino-cli 1.5.1). Default board options are correct — this FQBN enables **USB CDC
On Boot**, which the protocol depends on.

```sh
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3 firmware/xiao_first_light
arduino-cli upload -p <PORT> --fqbn esp32:esp32:XIAO_ESP32S3 firmware/xiao_first_light
```

Find `<PORT>` with `arduino-cli board list`. It is `/dev/cu.usbmodem*` on macOS and
`/dev/ttyACM*` on the Pi. If the board is not listed, hold **BOOT**, tap **RESET**,
release BOOT, and upload again.

## Identify the device on the Pi

Use the stable by-id path so a re-enumeration cannot point the runtime at some other
serial device:

```sh
ls -l /dev/serial/by-id/
```

Grant access through group membership, never `chmod 777`:

```sh
sudo usermod -a -G dialout $USER   # log out and back in to take effect
```

**Close any serial monitor before starting the runtime.** The port is exclusive: a
running `arduino-cli monitor`, `screen` or IDE monitor will make the runtime report the
device as unavailable.

## Run the Pi runtime on the serial transport

`--esp-url` and `--esp-serial` are mutually exclusive and one is required. There is no
fallback between them: a misconfigured run fails closed instead of quietly commanding
the wrong endpoint.

```sh
.venv/bin/python -m pip install -r requirements-hardware.txt   # pyserial, optional tier

.venv/bin/python -m dcamr.main \
  --release <bundle>/release \
  --trust-key <bundle>/trust/manifest_public.hex \
  --data-dir <pi-data> \
  --local-test-storage \
  --initialize-ledger \
  --esp-serial /dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit-if00 \
  --host 127.0.0.1 --port 8099
```

Use `--usb-root` with `--ledger-key-file` instead of `--local-test-storage` for a real
USB ledger; `--initialize-ledger` is first provisioning only. `--serial-baud` (115200)
and `--serial-timeout` (2.0 s) are available if needed.

Drive it with the existing signed terminal client:

```sh
.venv/bin/python -m lab.first_light.terminal_client --url http://127.0.0.1:8099 \
  --key-file <bundle>/client/term-agent-01-k1.seed --state on --repeat 2

.venv/bin/python -m lab.first_light.terminal_client --url http://127.0.0.1:8099 \
  --key-file <bundle>/client/term-agent-01-k1.seed --state off
```

## Expected outcomes

| Action | Physical | Response | Audit |
| --- | --- | --- | --- |
| Signed `state=on` | LED lights | `decision=ALLOW execution=COMPLETED observed=on` | REQUEST, ASSESSMENT, DECISION, EXECUTION_ATTEMPT, CONTROLLER_RECEIPT, EXECUTION_RESULT, OBSERVED_STATE |
| Same envelope repeated | **no change** | same payload plus `idempotent_replay` | no new events |
| Unknown agent | **no change** | `HTTP 401 DENY UNKNOWN_KEY` | REJECTION only |
| Node unplugged mid-run | last output held | `execution=UNKNOWN observed=None` | EXECUTION_ATTEMPT then UNKNOWN result |

A denied request never reaches the device, even when the light is already on.

## Diagnosis

| Symptom | Cause and fix |
| --- | --- |
| Board never appears as a port | **Charge-only USB cable.** Most bundled cables carry power only. Swap for a known data cable; the port appears within a second of plugging in. |
| `serial device unavailable` at startup | Wrong path, or a serial monitor still holds the port. Close the monitor; confirm with `ls -l /dev/serial/by-id/`. |
| `pyserial is not installed` | `pip install -r requirements-hardware.txt`. |
| Port exists but every command is UNKNOWN | USB CDC On Boot disabled, or firmware not actually flashed. Recompile with the stock FQBN options and re-upload. |
| Board resets when the runtime starts | Something is asserting DTR/RTS. The runtime holds both low; a serial monitor attached at the same time will not. |
| Commands acknowledged but the LED stays dark | Wiring. Check LED polarity (long leg to the resistor), that the resistor is in series with the anode, and that the LED is on D0 and not another pad. The node reports its own output, so it will happily report `on` into a broken circuit. |
| Both LEDs lit before any command | Expected on a fresh board with something on D6 — see wiring above. The XIAO's own power indicator is also always on and is not firmware-controlled. |

## Verification and remaining work

Performed on a development Mac with the board attached: firmware compiled for
`esp32:esp32:XIAO_ESP32S3`, flashed and verified; ON/OFF/readback over real USB CDC;
the full signed pipeline producing ALLOW/COMPLETED/`observed=on` with the seven-event
chain; a repeated envelope replaying with no second device write; an unknown-agent
request refused with no device write.

Not yet done: the same run on the Raspberry Pi 4B itself, over the Pi's USB port and
against a USB-backed ledger. Nothing here has been deployed to the Pi.

`observed_state` is the node's own driven output, not measured illumination — a dead
LED still reports `on`. Exactly-once physical execution is not claimed across
arbitrary crashes or lost acknowledgments; the tested guarantee is that one signed
request produces at most one device write and unprovable outcomes are recorded as
UNKNOWN.
