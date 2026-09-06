# Local agent model setup — 2026-09-06

Baseline: `11ccd6aaa340742796cb2fb350f4db847d1a3f6f` on `main`, matching both
locally available remote-tracking main refs. Work is on
`codex/local-agent-model-setup`. Follow [AGENTS.md](../../AGENTS.md).
The user authorized installing/downloading/configuring the local models after
their teammate authorized the Mac's SSH public key. This did not authorize
starting/resetting the plant or running the cooling/power actuation sequence.

## Host and Pi connection

- Mac: 16 GiB RAM; approximately 104 GiB disk available before installation.
- Pi Ed25519 public host fingerprint was independently fetched and matched
  `SHA256:uFZ6XoYVJ6PevSXSi2kyGQeM9XV/P6pks125tDddPEY` before being added to
  the existing `~/.ssh/known_hosts`; existing entries were preserved.
- Key-authenticated `pi@192.168.50.20` login and `sudo -n true` pass.
- `systemctl show -p Id -p ActiveState -p MainPID` reports light-mcp and
  alice-thermal-demo active, alice-runtime inactive. The thermal MainPID command
  is `/home/pi/Alice/.venv/bin/python -m services.thermal_demo.server --port 8080`.
- A loopback-only Mac `8790` SSH forward connects to the existing Pi MCP.
  An unauthenticated GET returns 401. SSH uses keepalives and exits on forward
  setup failure; its control socket is `~/.config/alice/agents/mcp-ssh.sock`.
- Each existing cooling/power/observer MCP token is 43 characters and is stored
  in its own private mode-0600 file. Token values were never printed. The Pi
  operator token was used only by an SSH-launched GET on Pi loopback and never
  copied to this Mac.

The plant was already RUNNING, run `7cc0202c8c0245f8bcf631477a5a4f6c`, revision 1,
fan target 70%, battery 80%, and one existing request. Initial observed temperature
was about 206.7 F and continued evolving during the read-only checks. This is not
the requested Part 2 READY 90/60/60 baseline. No lifecycle or fan action was sent.

## Installation and configuration

| Component | Result |
| --- | --- |
| Root Python environment | Existing Python 3.11 preserved; `mcp==1.29.1`, `PyYAML==6.0.3` and dependencies installed from `requirements-light-mcp.txt`; `pip check` passes |
| Goose | Homebrew `block-goose-cli` 1.45.0 installed; automatic Homebrew update and cleanup disabled for this installation |
| Qwen | Downloaded `qwen2.5:7b` (7.6B Q4_K_M, 4,683,087,332 bytes); created `qwen2.5-tools` with 32,768 context tokens and temperature 0.1; real Goose read-only tool use passes |
| Existing Llama models | `llama3.1:8b` and `dolphin-llama3:latest` retained; both produced valid local JSON responses |
| Facial identity | Existing InsightFace `buffalo_l` detection/ArcFace assets retained; real public-image inference checks pass |
| Live facial support | Existing `face_landmarker.task` and `MiniFASNetV2.onnx` hashes match the pinned assets; service reports identity/pose/PAD PASS and READY |
| Pi anomaly model | Existing 950,520-byte `alice-fan-hybrid-experiment-v1` artifact with cooling/power profiles verified present; no deployment or replacement |

The Pi fan-model SHA256 is
`4f10803e19979a278990fb0a03a6bea4c27174d2a6c57c58a07f9bb3070049f2`.
The scorer also passed direct synthetic inference on the Pi: cooling 60→70,
70→80 and 80→90 at 90 F scored LOW (0.5013, 0.3091 and 0.7901); power 90→0
scored HIGH (1.0). Load took 0.0786 s and these individual scores about
0.0011–0.0013 s. These are bounded installation probes, not a benchmark or
new signed runtime proposals. No ledger, plant or serial owner was opened.

Goose default settings select local Ollama/Qwen. Three isolated profile roots
under `~/.config/alice/agents/<agent-id>/` bind each process to its selected token
through `env_keys` and an Authorization-header placeholder. The observer profile
exposes only `get_metrics`; cooling and power expose `get_metrics` and
`set_fan_speed`. No developer/filesystem extension was added. The new
[launcher](../../scripts/lab/run_local_agent.py) selects the private profile and
supports read-only `--check` or a user-requested `--text` conversation.
The [host guide](../guides/local-agent-host.md) records normal usage and reconnects.

## Commands and verification

Commands and API checks below were actually run.

- `.venv/bin/python -m pip install -r requirements-light-mcp.txt`: succeeded.
- `HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 brew install block-goose-cli`:
  succeeded; `goose --version` reports 1.45.0.
- `.venv/bin/python -m pip check`: no broken requirements.
- `services/biometrics/.venv/bin/python scripts/biometrics/setup_live_models.py`:
  existing pose and PAD assets checksum-verified; no replacement required.
- `services/biometrics/.venv/bin/python scripts/biometrics/smoke_arcface.py`:
  temporary public-image enrollment and identity match pass; no-face and
  multiple-face cases blocked. Existing enrollment storage and camera untouched.
- Authenticated GET `/live/readiness`: READY, identity/pose/PAD PASS under
  `alice.live-face.v3`. The older identity-only `/health` and smoke output's
  `liveness: NOT_CONFIGURED` label does not describe the live pose/PAD endpoint.
- Local `/api/chat` JSON smoke with `keep_alive:0`: Llama 3.1 passed in 7.19 s;
  Dolphin Llama 3 passed in 4.83 s. These are short installation checks, not
  application-quality or throughput benchmarks.
- `run_local_agent.py --agent <each of the three identities> --check`:
  authenticated MCP initialization, two-tool discovery and `get_metrics` pass.
  All return the existing run, revision 1 and one request; no fan proposals.
- Goose observer probe with temporary Llama 3.1 model override: one
  `machine_metrics/get_metrics` call returned RUNNING, fan target 70%, battery 80%.
  This verified provider/profile/header/tool wiring before Qwen finished downloading.
- `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_metrics_integration.py`:
  **8 passed** with temporary loopback servers, in 6.24 s. Twelve MCP API
  deprecation warnings; no test contacted the Pi. The preceding audit's 41
  targeted passes are historical evidence from the earlier read-only turn.
- SSH-launched `.venv/bin/python -c` importing only `FanModel`: the existing Pi
  model loads and directly scores the four synthetic proposals as LOW/LOW/LOW/HIGH.

- Ollama 0.21.0 `/api/pull` downloaded `qwen2.5:7b` and returned success.
  `ollama create qwen2.5-tools --file ~/.config/alice/agents/qwen2.5-tools.Modelfile`
  created the alias from the existing downloaded layers. `/api/show` confirms
  completion/tools capabilities, parent Qwen 7B and `num_ctx 32768`.
- Final `run_local_agent.py --agent observer-agent-01 --text ...` used Qwen,
  called `machine_metrics/get_metrics`, correctly reported fan target 70% and
  battery 80%, labelled them simulated, and exited 0. No actuator tool was exposed.
  Ollama `/api/ps` reports context length 32,768 and 8,210,446,336 bytes loaded
  in device memory. The full alias manifest digest is
  `721ed35bfe08b83c62c8882a0e6e6b6f64151a0b2b81f5fe6b9445f7946b5348`.
- Final authenticated metrics retain the same run ID, revision 1 and exactly one
  existing request. The target remains 70%, battery 80%; temperature reached
  about 209.9 F as the existing simulation continued. No new request was created.
- Ollama CLI help initially failed inside the sandbox's restricted native Metal
  environment. Its rerun with native access passed; the existing server and
  subsequent real model inference remained operational.
- `git diff --check`, launcher syntax/help, document-link checks, tracker ID
  uniqueness and current snapshot size checks passed. Private token values are
  absent from the launcher, guide, report and Goose configurations.

## Remaining acceptance

- The operator must coordinate any plant reset/start and the later cooling/power
  demo. No full Part 2 or fresh human camera/technician rejection was performed.
- The existing console feed remains the saved local-runtime/mock-controller feed.
  Agent-host setup does not configure the separate technician machine.
- Decision-Brief MCP live `AliceSource`, automatic agent triggers, authority
  transfer and real-sensor model acceptance remain outside this setup.
- No cloud API key, cloud model call, repository push or Pi deployment occurred.

The previous current snapshot is preserved in the
[pre-setup checkpoint](../handoffs/2026-09-06-before-local-model-setup.md).
