export function event(sequence = 1, type = 'REQUEST', request = 'request-1') {
  return {
    schema_version: 'alice-audit-event-v1',
    canonicalization_version: 'alice-json-v1',
    ledger_id: 'ledger-1',
    node_id: 'pi-1',
    event_id: `event-${sequence}`,
    sequence,
    event_type: type,
    previous_hash: sequence === 1 ? '0'.repeat(64) : String(sequence - 1).padStart(64, '0'),
    event_hash: String(sequence).padStart(64, '0'),
    outbox_id: `event-${sequence}`,
    initial_state: 'LOCAL',
    time: {
      recorded_at: '2026-09-06T01:00:00Z',
      confidence: 'UNCERTAIN',
      clock_source: 'pi-clock',
      boot_id: 'boot-1',
      monotonic_ns: '1000000',
    },
    correlation: {
      correlation_id: request,
      request_id: request,
      request_sha256: 'a'.repeat(64),
      assessment_id: null,
      action_id: null,
      execution_id: null,
      parent_event_id: null,
    },
    attribution: {
      agent_id: 'agent-1',
      actor_kind: 'AGENT',
      actor_id: 'agent-1',
      authenticated_requester_id: 'agent-1',
      responsible_user_id: null,
      delegator_id: null,
      technician_id: null,
      assignment_source_id: null,
      resolution: 'RESOLVED',
    },
    authority: {
      product_mode: 'OFFLINE',
      connectivity: 'DISCONNECTED',
      execution_owner: 'ALICE',
      authority_interval_ref: 'interval-1',
      confirmation: 'CONFIRMED',
    },
    provenance: {
      policy: { id: 'release-1', sha256: 'b'.repeat(64), missing_reason: null },
      baseline: { id: null, sha256: null, missing_reason: 'NOT_APPLICABLE' },
      model: { id: null, sha256: null, missing_reason: 'NOT_APPLICABLE' },
      calibration: { id: null, sha256: null, missing_reason: 'NOT_APPLICABLE' },
      snapshot: { id: null, sha256: null, missing_reason: 'NOT_APPLICABLE' },
      evidence: [],
    },
    detail: {
      outcome:
        type === 'DECISION' ? 'ALLOW' : type === 'EXECUTION_RESULT' ? 'COMPLETED' : 'ADMITTED',
      reason_codes: [],
    },
  };
}
export const page = (events: unknown[]) => ({
  schema_version: 'alice-runtime-feed-v1',
  source: { connection: 'local-runtime', controller: 'mock' },
  events,
});
