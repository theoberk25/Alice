# Read-only demo LED mapping

This increment implements only supplied values -> eight pattern descriptions.
No environmental model, agent, decision, network access, GPIO, serial writes,
firmware changes, background worker or service installation is included.

## Input

Exactly four fields are required:

```json
{"temperature_f":140,"fan_pct":80,"power_w":451.2,"battery_pct":60}
```

Fan means applied/actual fan speed. Power is supplied, never computed here.
Numeric values must not be strings or booleans. Null or nonfinite numbers make
only the affected pair UNAVAILABLE. Missing/extra fields are errors. Finite
out-of-range inputs clamp to display endpoints; this is not sensor validation.
The caller passes `stale=True` when its source is stale; all patterns then become
UNAVAILABLE. This module has no clock or source freshness assumptions.

## Mapping

| Channels | Color | Variable | Behavior |
| --- | --- | --- | --- |
| 01,05 | Yellow | Power W | Linear 0.5–5 Hz across 400–500 W |
| 02,06 | Blue | Fan % | Zero/off below or at 0%; otherwise linear 0.5–5 Hz across 0–100% |
| 03,07 | Red | Temperature F | Linear 0.5–5 Hz across 80–175 F |
| 04,08 | White | Battery % | Segments 0–50 and 50–100% |

Targets retain the color ordering from services/light_mcp/machines.yaml. That file
and the signed execution contracts are unchanged. Other pairs blink in phase
when the future renderer starts their matching patterns together.

White: empty segment OFF; full segment SOLID; partial segment blinks from 0.5 Hz
near full to 5 Hz near empty. At 60%, first white is SOLID, second 4.1 Hz. At 50%,
first SOLID and second OFF; at 100%, both SOLID; at zero both OFF. White's blink
rate denotes depletion within its active segment, unlike the other colors.
These are demo display endpoints, not thermal safety or power policy limits.

## API and preview

`dcamr.display.led_patterns.map_patterns(values, stale=False)` returns an immutable
tuple of frozen Pattern values. `display_document` produces JSON-compatible
`alice-led-display-v1`: target, color, variable, segment, mode, hz, duty_cycle.
Hz means complete on/off cycles per second; BLINK uses 50% duty. OFF and
UNAVAILABLE have zero duty/rate; SOLID has duty 1 and rate 0. UNAVAILABLE remains
a distinct status, even if a later renderer chooses an unlit physical output.

Run from the checkout root:

```sh
python3 -m lab.led_preview --temperature-f 140 --fan-pct 80 --power-w 451.2 --battery-pct 60
python3 -m unittest discover -s tests -p test_led_patterns.py
```

## Next increment: renderer, not part of this change

Consume these patterns without resetting phase on every telemetry update.
A possible 10 Hz input refresh is independent of blink timing. At 5 Hz, each
half-cycle lasts 100 ms. A nominal 200 Hz local timing loop provides 20 steps per
half-cycle, but USB/OS scheduling cannot promise that precision. Inspect the
current single-owner serial path and prefer firmware timing before implementation.
Never start a second serial writer or translate every blink into an agent action.

## Verification

Eight tests passed: channel/color agreement with existing configuration, endpoints,
pair agreement, white boundaries/60% behavior, depletion monotonicity, clamping,
stale/invalid input handling, and independent nonmutating projections. Preview CLI
produced JSON successfully. No physical verification is claimed.
