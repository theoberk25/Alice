# Plan — Part 1: cloud governed request through the enterprise ingress

Updated: 2026-09-06. Read [AGENTS.md](../../AGENTS.md) and [current.md](../../current.md)
first. Story: [docs/demo.md](../demo.md) "Part 1 — connected enterprise operation".
This plan gets the **connected / ONLINE** opener working: the Google ADK cloud
agent submits **one signed governed request** that the enterprise host audits
(Wazuh receipt) **before** the Pi decides, and the same request_id is shown
correlated in the enterprise SIEM and the technician surface.

This is discovery-verified as of 2026-09-06; do not assume, re-check each ✓ below.

## Outcome / definition of done

A single `set_demo_fan_pct` action, signed by the cloud agent's
provisioned key, is:

1. POSTed to the current enterprise ingress at `http://192.168.50.150:8790/request`,
2. verified there and written to Wazuh as an **enterprise receipt** (`verified:true`),
3. forwarded unchanged through the enterprise host's SSH tunnel to the Pi thermal
   `/request`, which returns the model-backed decision and application state,
4. visible with the **same request_id** in the enterprise SIEM console (`.150:8786`)
   and in the technician console, with the Pi USB ledger holding the event chain.

Never resubmit the same request_id; a repeat returns the stored outcome.

## Topology (verified live)

| Host | Address | Role | State |
| --- | --- | --- | --- |
| This Mac | `192.168.50.10` | runs the cloud agent (`adk web` / CLI) | on LAN ✓ |
| Enterprise/SIEM Mac (Jared) | `192.168.50.150` | ingress `:8790`, SIEM console `:8786`, Wazuh | ingress `/health`=200 ✓ |
| Pi | `192.168.50.20` | `alice-thermal-demo.service` `:8080` (loopback), decides | active ✓ |

`.150` is the address currently assigned to the enterprise Mac on ALICE-NETWORK;
the earlier `.50` reservation is not assigned. Re-run the health check and update
the client environment if the router later assigns a different address.

The Pi runtime binds loopback. The ingress therefore forwards to the enterprise
host's `127.0.0.1:18080` SSH tunnel, never a broadly exposed Pi listener.

## Preconditions to confirm (do not skip)

- [ ] Ingress healthy: `curl -s http://192.168.50.150:8790/health` → 200.
- [ ] Pi thermal runtime up: `ssh pi@192.168.50.20 'systemctl is-active alice-thermal-demo.service'` → `active`.
- [ ] SIEM console reachable: `curl -s -o /dev/null -w '%{http_code}\n' http://192.168.50.150:8786/` (expect 200). Wazuh is seeded with the DN-Hacks scenario (Jared `87fe559`).
- [ ] Pi SSH host key matches `SHA256:uFZ6XoYVJ6PevSXSi2kyGQeM9XV/P6pks125tDddPEY`.

## Blockers this plan resolves

### B1 — Provision the cloud agent identity (private material; NOT in the repo)

The cloud agent needs an `agent_id` and its **private Ed25519 seed (hex)** whose
public half is trusted by **both** the ingress (`--keys`) and the Pi's signed
release. Ask Theo where these live (this Mac / the Pi / `.50`). Use a fan-permitted
thermal identity such as `cooling-agent-01` (`key_id` = `cooling-agent-01-k1`).

- [ ] Obtain `ALICE_AGENT_ID` (`cooling-agent-01`) and the seed file path.
- [ ] Confirm the id is trusted on the Pi:
      `ssh pi@192.168.50.20 'python3 -c "import json;print(sorted(json.load(open(\"/mnt/alice-usb/thermal-release/terminal_keys.json\")).keys()) if isinstance(json.load(open(\"/mnt/alice-usb/thermal-release/terminal_keys.json\")),dict) else \"list\")"'`
      (adjust to the file's actual shape; you only need the **id names**, never the key bytes).
- [ ] Confirm the ingress owner (Jared) has the same public key registered.

Handling secrets: keep the seed out of chat, git, and the transcript. Reference it
only by absolute path. Do **not** print seed contents.

### B2 — Wire the cloud agent env and restart `adk web`

The `submit_governed_fan_request` tool attaches only when
`ALICE_THERMAL_REQUEST_URL` is set before `adk web` starts.

Edit `cloud/adk_light_agent/.env` (gitignored) to add:

```dotenv
ALICE_THERMAL_REQUEST_URL=http://192.168.50.150:8790
ALICE_AGENT_ID=cooling-agent-01
ALICE_AGENT_KEY_FILE=<absolute path to the private Ed25519 seed hex>
```

Keep `GOOGLE_API_KEY` (already set). Then restart the ADK UI so it rebuilds
`root_agent` with the tool:

```bash
# stop the current adk web (:8000), then from cloud/ with the venv active:
adk web --host 127.0.0.1 --port 8000
```

## Run the opener

**Rehearse with a dry run first (no send, validates signing):**

```bash
.venv/bin/python -m cloud.thermal_governed_client --dry-run --fan-pct 70
```

**Then fire the real governed request.** Two equivalent surfaces — pick one:

- Deterministic CLI (recommended for reliability):

  ```bash
  .venv/bin/python -m cloud.thermal_governed_client \
    --url http://192.168.50.150:8790 --fan-pct 70 \
    --run-id <current-run-id> --expected-revision <current-revision>
  # expect an enterprise receipt plus the Pi decision/application
  ```

- Live model (for the on-stage "agent decides" visual): in `adk web` (`:8000`),
  pick `machine_ops_cloud`, prompt it to read metrics and increase the fan by
  10 percentage points. It should call `submit_governed_fan_request` exactly once and
  report the enterprise receipt + decision. It must NOT resubmit.

This is an **actuating, outward action** — get Theo's explicit go before firing
the non-dry-run submit.

## Verify correlation

- [ ] Capture the `request_id` from the submit output.
- [ ] Enterprise SIEM (`http://192.168.50.150:8786`): the enterprise receipt for
      that request_id appears (verified), correlated with the Pi decision.
- [ ] Technician surface shows the same request_id + decision.
- [ ] Pi ledger holds the chain (read-only check on the Pi):
      `ssh pi@192.168.50.20 'ls -1 /mnt/alice-usb/pi-data | tail'` and/or the
      pipeline checker from the runbook if a request-id lookup is needed.
- [ ] Same agent_id / responsible identity / signature preserved end to end.

## Risks / watch-outs

1. **Ingress → Pi reachability.** If submission returns a 502, verify the enterprise
   host's `18080 → Pi 8080` SSH tunnel. Do not expose Pi port 8080 to the LAN.
2. **401 unknown signature.** Means the agent's public key is not trusted by the
   ingress/Pi. Fix provisioning (B1); do not "retry" with a new id.
3. **Opt-in tool missing.** If the model never calls `submit_governed_fan_request`,
   `ALICE_THERMAL_REQUEST_URL` was not set before `adk web` started — restart it.
4. **Idempotency.** One request_id, one outcome. To rehearse again, use a fresh
   request (new id), not a resubmit.

## References

- Integration contract: [docs/integration/cloud-agent-enterprise-ingress.md](../integration/cloud-agent-enterprise-ingress.md)
- Cloud client: [cloud/thermal_governed_client.py](../../cloud/thermal_governed_client.py)
- Agent + opt-in tool: [cloud/adk_light_agent/agent.py](../../cloud/adk_light_agent/agent.py)
- Ingress service: [services/enterprise_ingress.py](../../services/enterprise_ingress.py)
- SIEM console + Wazuh seed: `scripts/lab/enterprise_sim/` (Jared `87fe559`)
- Runbook: [docs/guides/demo-runbook.md](../guides/demo-runbook.md)
