# Run the environmental demo

Use Python 3.11+ and `pip install -r requirements-hardware.txt`. The
[contract](../contracts/environmental-demo-v1.md) covers API roles, agent integration,
policy, review and failure behavior. No frontend page or physical fan is required.

Generate local demonstration keys into a **new private directory**:

```sh
python -m lab.thermal_demo.build_release /tmp/alice-demo-bundle
```

Set `THERMAL_OPERATOR_TOKEN` to a private token and `THERMAL_AGENT_TOKENS` to a JSON
object mapping cooling-agent-01, power-agent-01 and observer-agent-01 to distinct
private bearer tokens. All three identities must match `agent-keys.json`. Do not
commit these tokens or generated keys. Start:

```sh
python -m services.thermal_demo.server \
  --release /tmp/alice-demo-bundle/release \
  --trust-key /tmp/alice-demo-bundle/manifest-public.hex \
  --agent-keys /tmp/alice-demo-bundle/agent-keys.json \
  --fan-model-file /path/to/reviewed/model.json \
  --data-dir /tmp/alice-demo-ledger
```

Add `--console-trust-file /path/to/provisioned-console-trust.json` for signed native
review using the existing [native review setup](native-runtime-review.md). The
server starts without review trust, but held requests cannot be approved then.
No new biometric bypass or synthetic proof generator is included in this launcher.

For the existing native console, start its normal `services.runtime_feed` bridge
with upstream `http://127.0.0.1:8795`, source `local-runtime`, controller `mock` (the
fan is simulated), `ALICE_FEED_TOKEN` for the console, and `ALICE_UPSTREAM_TOKEN`
set to the demo operator token. Configure the console's existing feed/review URL
and token to this bridge. Its strict request view displays the simulated fan
percentage, run and revision, retaining exact parameters and signed consent.
A teammate can build the operator page against the three-field API independently.

Configure then Start using the operator API. Agent code can use:

```python
import os
from services.thermal_demo.client import DemoClient
client = DemoClient('http://127.0.0.1:8795', os.environ['COOLING_AGENT_TOKEN'])
state = client.state()
record = client.request_fan(state, 90, 'cooling-proposal-1')
```

Inspect the actual decision/application, then fresh state; do not locally apply a
proposal. A small, context-consistent change from either permitted agent executes
automatically. An unusual change, such as cutting a hot room's fan from 60% to 0%,
produces a model-backed HOLD that requires signed human review. The local LLM may
explain the score but cannot approve it. An observer request is denied by policy.
Stop before reconfiguration.

Add `--esp-serial /dev/serial/by-id/...` only on a separately prepared Pi with the
v3 firmware and existing eight-channel wiring. Stop any other service owning that
port first. This implementation does not flash boards, install services or deploy.
Add `--energy-time-scale 60` only for explicitly labeled compressed battery energy;
thermal time remains unscaled. Readback is configured output, never visual proof.

Verify with `python -m pytest -q tests/test_thermal* tests/test_pattern_renderer.py
 tests/test_serial_firmware.py` (join into one shell line). Tests generate temporary
trust and use fake clocks, local sockets and host-compiled actual firmware. Real
camera, Arduino board build, wiring, LED appearance and Pi timing require separate
physical acceptance.

The reconciled agent interface is the teammate’s [machine-metrics MCP](../guides/machine-metrics-integration.md): `get_metrics()` and `set_fan_speed(value)` on :8790. The HTTP client is the internal adapter path to the same plant; no second fan state file is authoritative.
