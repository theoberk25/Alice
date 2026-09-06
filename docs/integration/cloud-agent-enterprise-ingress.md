# Integration — ADK cloud agent → enterprise-first ingress

Status: **cloud side implemented + verified locally** (2026-09-06). Rules: [AGENTS.md](../../AGENTS.md).
Related: [topology](../agent-build/topology.md) · [cloud agent build](../agent-build/01-cloud-agent.md) · [Wazuh audit sync](wazuh-audit-sync.md).

## Purpose

Promote the Google **ADK cloud agent** (`cloud/adk_light_agent`) from a standalone
local MCP client into a first-class node of the **enterprise-first** directed
flow. A governed action from the cloud agent becomes a *signed request* that is
received and audited by the enterprise host **before** the Pi decides — not the
old operator-first path where the operator submits straight to the Pi and Wazuh
only sees the Pi's later audit.

```
ADK cloud agent
  └─ submit_governed_request (signs with the agent's provisioned key)
       └─ POST <ingress>/request   ── enterprise receipt recorded in Wazuh (verified:true)
            └─ forward to Pi /request ── decision (CHALLENGE ⇒ HOLD), USB ledger, technician feed
                 └─ … Pi audit delivered back to Wazuh (existing worker)
```

The **request_id and the Ed25519 signature are preserved end to end**: the
ingress and the Pi verify the exact bytes the agent signed. Nothing in this path
turns an incoming event into a trusted permission or training data.

## Wire contract (unchanged, shared)

Envelope is exactly three keys — identical to the Pi `/request`, to
`scripts/lab/first_light/terminal_client.py`, and to `wireless-test.json`:

```json
{ "request": { "schema_version": "1.0", "request_id": "...", "agent_id": "...",
               "action": "set_light_state", "target": "ESP-LIGHT-01",
               "parameters": { "state": "on" }, "issued_at": "…Z" },
  "key_id": "<agent>-k1",
  "signature": "<base64 Ed25519 over canonical_bytes(request)>" }
```

`canonical_bytes` is the one authoritative canonicalization in
[`dcamr/audit/event_contract.py`](../../dcamr/audit/event_contract.py) (UTF-8,
sorted keys, `separators=(",",":")`). The client reuses it — no second format.

### Ingress `/request` response (what the client expects)

```json
{ "enterprise_receipt": { "verified": true, "request_id": "...", "key_id": "...",
                          "received_at": "…Z", "request_sha256": "...",
                          "signature": "<preserved>", "wazuh_indexed": true },
  "pi": { "request_id": "...", "decision": "CHALLENGE",
          "reason_code": "PERMISSION_REVIEW_REQUIRED",
          "execution": null, "observed_state": null },
  "decision": "CHALLENGE" }
```

HTTP status mirrors the Pi: **202** CHALLENGE, 200 ALLOW/executed, 403 DENY,
**401** bad/unknown signature (and the ingress must **not** forward it),
409 request-id conflict, 503 audit-not-ready.

## What this change adds (this repo, this branch)

| Piece | Path | Notes |
| --- | --- | --- |
| Cloud ingress client | [`cloud/enterprise_ingress_client.py`](../../cloud/enterprise_ingress_client.py) | build → sign → `/health` preflight → `/request`; **no hardcoded destination**; `dry_run` builds without sending. CLI: `python -m cloud.enterprise_ingress_client`. |
| Agent tool (opt-in) | [`cloud/adk_light_agent/agent.py`](../../cloud/adk_light_agent/agent.py) | `submit_governed_request` tool is added **only** when `ALICE_ENTERPRISE_INGRESS_URL` is set; default `adk web` behaviour (MCP tools only) is unchanged. |
| Local mock ingress | [`scripts/lab/enterprise_ingress/mock_ingress.py`](../../scripts/lab/enterprise_ingress/mock_ingress.py) | **Test stand-in**, loopback only. Verifies the signature, appends an enterprise receipt to a JSONL "Wazuh", synthesizes the Pi CHALLENGE (or `--pi-url` to forward for real). NOT the production `.50` service. |
| Tests | [`tests/test_enterprise_ingress_client.py`](../../tests/test_enterprise_ingress_client.py) | envelope contract; dry-run; end-to-end verified→CHALLENGE→receipted; unknown key rejected + not forwarded. |
| Config | [`.env.example`](../../.env.example) | `ALICE_ENTERPRISE_INGRESS_URL` (+ reuses `ALICE_AGENT_ID` / `ALICE_AGENT_KEY_FILE`). |

## Verify locally (no `.50`, no Pi, no ESP)

```bash
# 1. a throwaway agent key + its public half for the mock ingress
python - <<'PY'
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pathlib import Path
sk = Ed25519PrivateKey.generate(); Path("artifacts/enterprise-ingress").mkdir(parents=True, exist_ok=True)
Path("artifacts/enterprise-ingress/agent.key").write_text(sk.private_bytes_raw().hex())
keys = Path("artifacts/enterprise-ingress/pubkeys"); keys.mkdir(exist_ok=True)
(keys/"elec-agent-01-k1.pub").write_bytes(sk.public_key().public_bytes_raw())
PY

# 2. run the mock ingress (loopback)
python -m lab.enterprise_ingress.mock_ingress --keys artifacts/enterprise-ingress/pubkeys --port 8790 &

# 3. submit one governed request as the cloud agent would
ALICE_AGENT_ID=elec-agent-01 ALICE_AGENT_KEY_FILE=artifacts/enterprise-ingress/agent.key \
  python -m cloud.enterprise_ingress_client --url http://127.0.0.1:8790 --state on
#   → HTTP 202  receipt.verified=True  decision=CHALLENGE
```

Or just run the suite: `.venv/bin/python -m pytest tests/test_enterprise_ingress_client.py -q`.

## Boundaries / not done here (need owners + authorization)

- **The production ingress on `192.168.50.50:8790`** (network-listening,
  signature-verifying, real Wazuh receipt) is the enterprise-host workstream —
  the mock is only a local stand-in. Exposing a previously loopback-only service
  to the network is a real attack-surface change: verify-then-forward, always.
- **Restoring Wazuh + draining the Pi audit** (priority #1) and the **Pi USB
  ledger / ESP** steps run on other hosts and hardware.
- **The separate enterprise permissions-cache activation**
  (`cloud/permissions_cache.py`, `/mnt/alice-usb/enterprise-cache`) is a distinct
  path and is not wired into runtime by this change.
- **Vertex/Agent Engine stays gated** behind the human checkpoint in the build doc.
- Keep the permission-triggered **HOLD** for this integration test; live ML and
  automatic ONLINE/OFFLINE authority transfer remain separate work.
