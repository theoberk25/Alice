# Local agent host

Follow [AGENTS.md](../../AGENTS.md) and [current.md](../../current.md).
This guide covers the workstation installation, not plant startup. The
[machine-metrics contract](machine-metrics-integration.md) defines the tools;
the [Part 2 plan](../plans/2026-09-06-demo-part2-local-agent-workflow.md) defines
the later ALLOW/HOLD sequence. The technician console can run on another Mac.

## Installed topology

- One local Ollama server: `http://127.0.0.1:11434`.
- Agent model: `qwen2.5:7b`, with the `qwen2.5-tools` alias configured for 32,768
  context tokens. Cooling and power reuse the same weights, with separate identities.
- Existing console model: `llama3.1:8b`; the installed
  `dolphin-llama3:latest` is retained. Both run through the existing Ollama server.
- Goose CLI uses separate `GOOSE_PATH_ROOT` directories for cooling, power and
  observation. The ordinary Goose profile selects local Qwen with no extensions.
- Agent MCP: Mac `127.0.0.1:8790/mcp` through SSH to Pi `127.0.0.1:8790/mcp`.
  The Pi MCP delegates to the single thermal runtime on Pi loopback `8080`.
- ArcFace identity, MediaPipe pose and MiniFASNet presentation models remain in
  the existing biometric service. The synthetic fan anomaly model runs on the Pi.

No OpenAI, Gemini or other cloud-model API key is needed for this local path.
ALICE bearer tokens authenticate the agents independently of the local model.

## Private profiles and credentials

Host-local material is under `~/.config/alice/agents/<agent-id>/`:

| File/directory | Purpose |
| --- | --- |
| `mcp.token` | One preprovisioned agent bearer token; mode 0600 |
| `config/config.yaml` | Goose provider, model and authenticated MCP configuration |
| `work/` | Working directory for that agent's Goose runs |
| `data/`, `state/` | Goose's per-profile runtime state when created |

The alias Modelfile is `~/.config/alice/agents/qwen2.5-tools.Modelfile` and
reuses the base model layers. Directories are private. Configuration references `Bearer $LIGHT_MCP_TOKEN`
with `env_keys: [LIGHT_MCP_TOKEN]`; it does not contain token values.
The launcher reads only the selected identity's token. Observer's Goose profile
exposes only `get_metrics`; cooling and power expose both governed tools.
The Pi still enforces identity and permissions independently of tool filtering.

Tokens come from the Pi's existing `THERMAL_AGENT_TOKENS` mapping, not new keys
invented on this host. Preserve the Pi's operator token on the Pi. Never commit
credentials, Goose runtime state or model weights.

## Reconnect and check

Run from the checkout with its existing `.venv`. To repair dependencies:

```sh
.venv/bin/python -m pip install -r requirements-light-mcp.txt
.venv/bin/python -m pip check
```

First check whether the existing MCP forward is reachable:

```sh
curl --max-time 3 -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8790/mcp
```

401 means the authenticated MCP endpoint is reachable. Only if unreachable,
open the forward and leave its terminal running:

```sh
ssh -N -o BatchMode=yes -o ServerAliveInterval=15 -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:8790:127.0.0.1:8790 pi@192.168.50.20
```

An existing unexpected listener should be identified before changing anything.
This host needs no console port `18080` forward for the local agents.
The verified Pi Ed25519 host fingerprint is
`SHA256:uFZ6XoYVJ6PevSXSi2kyGQeM9XV/P6pks125tDddPEY`.

Read-only checks do not invoke an LLM or propose a fan change:

```sh
.venv/bin/python scripts/lab/run_local_agent.py --agent cooling-agent-01 --check
.venv/bin/python scripts/lab/run_local_agent.py --agent power-agent-01 --check
.venv/bin/python scripts/lab/run_local_agent.py --agent observer-agent-01 --check
```

To test local model tool use with only the read tool exposed:

```sh
.venv/bin/python scripts/lab/run_local_agent.py --agent observer-agent-01 \
  --text 'Read get_metrics once and report the plant status, fan target and battery.'
```

`--text` starts one Goose conversation. Selecting cooling or power gives that
process the governed proposal tool; use those conversations when running the
requested agent workflow. The launcher itself never starts/configures the plant,
approves reviews or generates replacement request IDs. The deterministic
`thermal_demo/drive_agents.py` remains the existing Part 2 actuation driver.

## Readiness boundaries

Successful model inference and authenticated metrics are host readiness, not a
completed demo. Before Part 2, the operator must separately coordinate the clean
90 F / 60% fan / 60% battery READY state and the later start. Do not reset an
existing teammate run as part of model installation. Maintain one ledger/serial
owner: thermal-demo active, ordinary alice-runtime inactive.

The Decision-Brief MCP's live `AliceSource` adapter remains unimplemented. Its
fixture server is not required for the two agents and is not enabled by this
setup. The existing technician console feed is a separate configuration; local
model installation does not repoint it to the Pi.

The installed Goose configuration follows its
[versioned configuration reference](https://github.com/aaif-goose/goose/blob/v1.45.0/documentation/docs/guides/config-files.md)
and [per-profile path implementation](https://github.com/aaif-goose/goose/blob/v1.45.0/crates/goose/src/config/paths.rs).
See the [host setup evidence](../reports/2026-09-06-local-agent-model-setup.md)
for the exact installed versions, model checks and outstanding acceptance.

## Integration dependency check

The [main integration report](../reports/2026-09-06-local-agent-main-integration.md)
records fresh validation against upstream `2aa5c34`. The separate biometric
environment deliberately uses headless OpenCV; its MediaPipe install uses
`requirements-live.txt --no-deps`. Therefore its `pip check` reports a missing
`opencv-contrib-python` distribution even though the tested imports and ArcFace
inference pass. Preserve the single provider; do not install a second cv2 package
merely to clear that metadata warning. Root agent-environment `pip check` passes.
