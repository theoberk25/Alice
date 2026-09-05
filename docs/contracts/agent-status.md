# Agent and service status

The original dashboard contract does not identify every running agent or model, so this repository adds `alice.agent_status`.

```json
{
  "schema_version": "1.0",
  "event_type": "alice.agent_status",
  "timestamp": "2026-09-05T15:44:04Z",
  "agent_id": "diagnostic-agent-04",
  "agent_type": "diagnostic",
  "model": "llama3.3:70b",
  "status": "WAITING_FOR_CONTEXT",
  "mission_id": "MISSION-291",
  "current_activity": {
    "type": "context_challenge",
    "label": "Preparing additional mission justification"
  },
  "health": "HEALTHY"
}
```

Statuses: STARTING, IDLE, RUNNING, WAITING_FOR_CONTEXT, VERIFYING_EVIDENCE, AWAITING_REVIEW, COMPLETED, FAILED, TERMINATED, OFFLINE. Health is HEALTHY, DEGRADED, FAILED, or UNKNOWN. Model strings are supplied by events and displayed unchanged; the mock roster is explicitly sample data and does not describe installed local models.

Services use `alice.service_status` with `service_id`, `label`, `status`, and optional `detail`. Status is READY, RUNNING, WAITING, IDLE, OFFLINE, FAILED, or UNAVAILABLE. These records describe operational activity such as “verifying two references,” never reasoning tokens or a scratchpad.
