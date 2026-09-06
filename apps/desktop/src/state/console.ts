import { create } from 'zustand';
import {
  normalizeEvent,
  TechnicianActionSchema,
  type Decision,
  type Infrastructure,
  type AgentStatus,
  type ServiceStatus,
  type Reconciliation,
  type AgentResponse,
  type TechnicianAction,
  type Verification,
  type ActionReceipt,
} from '@alice/contracts';
import { z } from 'zod';
import {
  transition,
  makeAction,
  canReview,
  indexDecision,
  rebuildDecisionIndexes,
  type HoldState,
  type HoldEvent,
  type AliceTransport,
  type LLMHealth,
} from '@alice/domain';
import { deterministicClarification, OllamaProvider } from '../lib/llm';
import { MockAliceTransport, RemoteAliceTransport } from '../lib/transport';
import { nativeCall, isNative, runtimeConfig } from '../lib/native';
import type { ScenarioName } from '../../../../fixtures/scenarios';
import { FeedStatusSchema, type FeedStatus } from '@alice/contracts';
import { emptyRuntime, mergeRuntimeFeed, type RuntimeState } from '@alice/domain';
export interface AuditEvent {
  id: string;
  timestamp: string;
  type: string;
  decision_id?: string;
  request_id?: string;
  detail: string;
}
export interface Technician {
  enrollment_pending?: boolean;
  enrollment_version?: 'IDENTITY_ONLY_V1' | 'MULTI_POSE_V2';
  technician_id: string;
  username: string;
  display_name: string;
  role: string;
  enabled: boolean;
  enrolled: boolean;
}
interface ConsoleState {
  runtime: RuntimeState;
  feed: FeedStatus;
  selectedRuntimeId: string;
  selectRuntime: (id: string) => void;
  ready: boolean;
  mode: 'mock' | 'remote';
  biometricMode: 'mock' | 'arcface';
  biometricPolicy: 'alice.live-face.v3';
  scenario: ScenarioName;
  decisions: Record<string, Decision>;
  requestDecisionHistory: Record<string, string[]>;
  latestDecisionByRequest: Record<string, string>;
  order: string[];
  selectedId: string;
  status?: Infrastructure;
  agents: Record<string, AgentStatus>;
  services: Record<string, ServiceStatus>;
  flows: Record<string, HoldState>;
  responses: Record<string, AgentResponse>;
  reconciliations: Record<string, Reconciliation>;
  actions: Record<string, TechnicianAction>;
  receipts: Record<string, ActionReceipt>;
  audit: AuditEvent[];
  errors: string[];
  technician?: Technician;
  llm: LLMHealth;
  contextSummaries: Record<string, string>;
  challenges: Record<string, string>;
  contextRequests: Record<string, string>;
  ingest: (event: unknown) => void;
  log: (type: string, detail: string, id?: string) => void;
  error: (message: string) => void;
  dismissError: () => void;
  select: (id: string) => void;
  advance: (event: HoldEvent, id?: string) => void;
  start: (scenario?: ScenarioName) => Promise<void>;
  hydrate: () => Promise<void>;
  restoreHistory: (input: unknown) => void;
  act: (
    action: TechnicianAction['action'],
    verification?: Verification,
    decisionId?: string,
  ) => Promise<void>;
  setTechnician: (technician?: Technician) => void;
  ask: (text: string) => Promise<string>;
  requestContext: (decisionId?: string) => Promise<void>;
  refreshLLM: () => Promise<void>;
}
let transport: AliceTransport;
let disconnect: (() => void) | undefined;
let epoch = 0;
const llm = new OllamaProvider();
const persistence = new Map<string, Promise<void>>();
export const useConsole = create<ConsoleState>((set, get) => ({
  runtime: emptyRuntime(),
  feed: {
    event_type: 'alice.feed_status',
    state: 'unavailable',
    last_success_at: null,
    message: 'No runtime feed connected',
  },
  selectedRuntimeId: '',
  selectRuntime: (selectedRuntimeId) => set({ selectedRuntimeId }),
  ready: false,
  mode: 'mock',
  biometricMode: 'mock',
  biometricPolicy: 'alice.live-face.v3',
  scenario: '03_hold_high_anomaly',
  decisions: {},
  requestDecisionHistory: {},
  latestDecisionByRequest: {},
  order: [],
  selectedId: '',
  agents: {},
  services: {},
  flows: {},
  responses: {},
  reconciliations: {},
  actions: {},
  receipts: {},
  audit: [],
  errors: [],
  llm: { status: 'OFFLINE', model: 'Not configured' },
  contextSummaries: {},
  challenges: {},
  contextRequests: {},
  error: (message) =>
    set((s) => ({
      errors: s.errors.includes(message) ? s.errors : [...s.errors.slice(-4), message],
    })),
  dismissError: () => set({ errors: [] }),
  log: (type, detail, id) => {
    const e = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      type,
      detail,
      decision_id: id,
      request_id: id ? get().decisions[id]?.request.request_id : undefined,
    };
    set((s) => ({ audit: [e, ...s.audit].slice(0, 500) }));
    if (isNative)
      void nativeCall('append_audit', { event: e }).catch((e) =>
        get().error(`Audit persistence failed: ${String(e)}`),
      );
  },
  select: (selectedId) => set({ selectedId }),
  setTechnician: (technician) => {
    set({ technician });
    if (isNative && get().mode === 'remote') {
      // Native feed reads require a current technician. Logout stops polling and
      // clears renderer copies; signing in starts the authoritative history replay.
      if (technician)
        void get()
          .start()
          .catch((e) => get().error(`Runtime connection failed: ${String(e)}`));
      else {
        ++epoch;
        disconnect?.();
        disconnect = undefined;
        set({
          runtime: emptyRuntime(),
          selectedRuntimeId: '',
          feed: {
            event_type: 'alice.feed_status',
            state: 'unavailable',
            last_success_at: null,
            message: 'Technician authentication required to read the live runtime',
          },
        });
      }
      return;
    }
    if (technician && isNative)
      void get()
        .hydrate()
        .catch((e) => get().error(`History could not be restored: ${String(e)}`));
  },
  hydrate: async () => {
    if (!isNative || get().mode === 'remote') return;
    get().restoreHistory(await nativeCall('read_console_history'));
  },
  restoreHistory: (input) => {
    if (get().mode === 'remote') return;
    const history = z
      .object({
        decisions: z.array(z.unknown()),
        actions: z.array(TechnicianActionSchema),
        annotations: z.array(z.unknown()),
        audit: z.array(
          z.object({
            id: z.string(),
            timestamp: z.string(),
            type: z.string(),
            detail: z.string(),
            decision_id: z.string().nullable().optional(),
            request_id: z.string().nullable().optional(),
          }),
        ),
      })
      .parse(input);
    const decisions = { ...get().decisions },
      flows = { ...get().flows },
      actions = { ...get().actions },
      responses = { ...get().responses },
      reconciliations = { ...get().reconciliations };
    for (const raw of history.decisions) {
      const d = normalizeEvent(raw);
      if (d.event_type !== 'alice.decision') throw new Error('Non-decision in decision cache');
      if (
        decisions[d.decision_id] &&
        JSON.stringify(decisions[d.decision_id]) !== JSON.stringify(d)
      )
        throw new Error('Immutable decision conflict during hydration');
      decisions[d.decision_id] = d;
      flows[d.decision_id] ??=
        d.decision.result === 'HOLD'
          ? d.context_challenge.required
            ? 'AWAITING_AGENT_RESPONSE'
            : 'AWAITING_TECHNICIAN'
          : 'RESOLVED';
    }
    const indexes = rebuildDecisionIndexes(decisions);
    for (const action of [...history.actions].reverse()) {
      if (!decisions[action.decision_id]) continue;
      actions[action.decision_id] = action;
      flows[action.decision_id] =
        action.action === 'APPROVE_ONCE'
          ? 'APPROVAL_SUBMITTED'
          : action.action === 'REJECT'
            ? 'REJECTED'
            : action.action === 'HOLD'
              ? 'HELD_BY_TECHNICIAN'
              : 'RESEARCHING';
    }
    for (const raw of history.annotations) {
      const e = normalizeEvent(raw);
      if (e.event_type === 'alice.agent_response') {
        const d = decisions[e.decision_id];
        if (
          !d ||
          d.request.request_id !== e.request_id ||
          d.request.agent_id !== e.agent_id ||
          (get().challenges[e.decision_id] ??
            d.context_challenge.challenge_id ??
            e.challenge_id) !== e.challenge_id
        )
          throw new Error('Stored agent response has invalid decision binding');
        responses[e.decision_id] = e;
      }
      if (e.event_type === 'alice.reconciliation') {
        if (!decisions[e.original_decision_id])
          throw new Error('Stored reconciliation has unknown decision');
        reconciliations[e.original_decision_id] = e;
      }
    }
    for (const d of Object.values(decisions)) {
      if (indexes.latestDecisionByRequest[d.request.request_id] !== d.decision_id)
        flows[d.decision_id] = 'SUPERSEDED';
      else if (
        responses[d.decision_id] &&
        !actions[d.decision_id] &&
        d.context_challenge.required &&
        d.decision.result === 'HOLD'
      )
        flows[d.decision_id] = 'REASSESSMENT_PENDING';
    }
    set((s) => ({
      ...indexes,
      decisions,
      flows,
      actions,
      responses,
      reconciliations,
      order: [...new Set([...s.order, ...Object.keys(decisions)])],
      selectedId:
        indexes.latestDecisionByRequest[decisions[s.selectedId]?.request.request_id ?? ''] ??
        s.selectedId,
      audit: history.audit.map((e) => ({
        ...e,
        decision_id: e.decision_id ?? undefined,
        request_id: e.request_id ?? undefined,
      })),
    }));
  },
  advance: (event, id = get().selectedId) =>
    set((s) => ({ flows: { ...s.flows, [id]: transition(s.flows[id] ?? 'IDLE', event) } })),
  ingest: (input) => {
    try {
      if (typeof input === 'object' && input !== null && 'event_type' in input) {
        if (input.event_type === 'alice.feed_status') {
          const feed = FeedStatusSchema.parse(input);
          set((s) => ({
            feed,
            errors:
              feed.state === 'live'
                ? s.errors.filter((e) => !e.startsWith('Runtime feed unavailable:'))
                : s.errors,
          }));
          return;
        }
        if (input.event_type === 'alice.runtime_feed') {
          if (get().mode !== 'remote') throw new Error('Runtime feed cannot mix with simulation');
          const { event_type: _type, ...page } = input;
          void _type;
          const runtime = mergeRuntimeFeed(get().runtime, page);
          set((s) => ({
            runtime,
            selectedRuntimeId: s.selectedRuntimeId || Object.keys(runtime.requests).at(-1) || '',
          }));
          return;
        }
      }
      if (get().mode === 'remote')
        throw new Error(
          'Remote mode requires validated runtime feed events; fixture records are disabled',
        );
      const e = normalizeEvent(input);
      if (e.event_type === 'alice.decision') {
        const prior = get().decisions[e.decision_id];
        if (prior) {
          if (JSON.stringify(prior) !== JSON.stringify(e))
            throw new Error(
              'Conflicting duplicate decision ID rejected. Upstream reassessment needs a new decision ID.',
            );
          return;
        }
        const indexes = indexDecision(get().decisions, get(), e);
        const previousId = e.reassessment?.previous_decision_id;
        set((s) => ({
          ...indexes,
          decisions: { ...s.decisions, [e.decision_id]: e },
          order: [e.decision_id, ...s.order],
          selectedId:
            !e.reassessment ||
            s.decisions[s.selectedId]?.request.request_id === e.request.request_id
              ? e.decision_id
              : s.selectedId,
          flows: {
            ...s.flows,
            ...(previousId
              ? {
                  [previousId]: transition(
                    s.flows[previousId] ?? 'RESOLVED',
                    'REASSESSMENT_RECEIVED',
                  ),
                }
              : {}),
            [e.decision_id]:
              e.decision.result === 'HOLD'
                ? e.context_challenge.required
                  ? 'HOLD_RECEIVED'
                  : 'AWAITING_TECHNICIAN'
                : 'RESOLVED',
          },
        }));
        const cached = isNative
          ? (persistence.get(previousId ?? '') ?? Promise.resolve()).then(() =>
              nativeCall<void>('cache_decision', { decision: e }),
            )
          : Promise.resolve();
        persistence.set(e.decision_id, cached);
        void cached.catch((err) => get().error(`Decision persistence failed: ${String(err)}`));
        get().log('DECISION_RECEIVED', `${e.decision.result} · ${e.request.action}`, e.decision_id);
        if (previousId) {
          get().log(
            'REASSESSMENT_RECEIVED',
            `New immutable assessment; parent ${previousId}`,
            e.decision_id,
          );
          get().log('DECISION_SUPERSEDED', `Superseded by ${e.decision_id}`, previousId);
          get().log(
            'CURRENT_ASSESSMENT_UPDATED',
            `Current assessment is ${e.decision_id}`,
            e.decision_id,
          );
        }
        if (e.decision.result === 'HOLD' && e.context_challenge.required) {
          get().log('HOLD_RECEIVED', 'Protected action remains blocked', e.decision_id);
          get().advance('REQUEST_CONTEXT', e.decision_id);
          const generation = epoch;
          const challenge = deterministicClarification(e);
          set((s) => ({
            challenges: { ...s.challenges, [e.decision_id]: challenge.challenge_id },
          }));
          void cached
            .then(() => transport.requestClarification(challenge))
            .then(() => {
              if (generation !== epoch) return;
              if (get().flows[e.decision_id] !== 'AUTO_CONTEXT_REQUEST') return;
              get().advance('CONTEXT_SENT', e.decision_id);
              get().log(
                'AUTO_CLARIFICATION_SENT',
                'Mission justification, expected effect, evidence, alternatives requested',
                e.decision_id,
              );
            })
            .catch((err) => {
              if (generation !== epoch) return;
              get().error(`Clarification not sent: ${String(err)}`);
              if (get().flows[e.decision_id] === 'AUTO_CONTEXT_REQUEST')
                get().advance('REVIEW', e.decision_id);
            });
        }
      } else if (e.event_type === 'alice.status') set({ status: e });
      else if (e.event_type === 'alice.agent_status')
        set((s) => ({ agents: { ...s.agents, [e.agent_id]: e } }));
      else if (e.event_type === 'alice.service_status')
        set((s) => ({ services: { ...s.services, [e.service_id]: e } }));
      else if (e.event_type === 'alice.reconciliation') {
        if (!get().decisions[e.original_decision_id])
          throw new Error('Reconciliation references an unknown decision.');
        set((s) => ({ reconciliations: { ...s.reconciliations, [e.original_decision_id]: e } }));
        get().log('EVIDENCE_RECONCILED', e.result.status, e.original_decision_id);
        if (isNative)
          void (persistence.get(e.original_decision_id) ?? Promise.resolve())
            .then(() => nativeCall('cache_annotation', { event: e }))
            .catch((err) => get().error(`Reconciliation persistence failed: ${String(err)}`));
      } else if (e.event_type === 'alice.agent_response') {
        const d = get().decisions[e.decision_id];
        if (
          !d ||
          d.request.request_id !== e.request_id ||
          d.request.agent_id !== e.agent_id ||
          (get().challenges[e.decision_id] ?? d.context_challenge.challenge_id) !== e.challenge_id
        )
          throw new Error('Agent response binding does not match the decision challenge.');
        set((s) => ({ responses: { ...s.responses, [e.decision_id]: e } }));
        if (get().flows[e.decision_id] === 'AWAITING_AGENT_RESPONSE') {
          get().advance('CONTEXT_RECEIVED', e.decision_id);
          get().advance('REASSESS', e.decision_id);
          get().log(
            'REASSESSMENT_PENDING',
            'Agent context received; awaiting a new upstream decision',
            e.decision_id,
          );
        }
        get().log(
          'AGENT_REJUSTIFICATION_RECEIVED',
          'Additional context received; original decision preserved',
          e.decision_id,
        );
        if (isNative)
          void nativeCall('cache_annotation', { event: e }).catch((err) =>
            get().error(`Context persistence failed: ${String(err)}`),
          );
        if (get().llm.status === 'READY')
          void llm
            .summarizeAgentResponse(e)
            .then((result) =>
              set((s) => ({
                contextSummaries: { ...s.contextSummaries, [e.decision_id]: result.summary },
              })),
            )
            .catch((err) => get().error(`Agent summary unavailable: ${String(err)}`));
      }
    } catch (err) {
      get().error(`Event rejected: ${String(err)}`);
    }
  },
  start: async (scenario = '03_hold_high_anomaly') => {
    const reset = get().ready;
    disconnect?.();
    const generation = ++epoch;
    persistence.clear();
    const config = await runtimeConfig();
    if (generation !== epoch) return;
    if (isNative && config.transport_mode === 'mock' && reset)
      await nativeCall('reset_mock_scenario');
    set({
      ready: false,
      runtime: emptyRuntime(),
      selectedRuntimeId: '',
      feed: {
        event_type: 'alice.feed_status',
        state: 'connecting',
        last_success_at: null,
        message: 'Connecting',
      },
      mode: config.transport_mode,
      biometricMode: config.biometric_mode,
      biometricPolicy: config.biometric_policy ?? 'alice.live-face.v3',
      scenario,
      decisions: {},
      requestDecisionHistory: {},
      latestDecisionByRequest: {},
      order: [],
      selectedId: '',
      status: undefined,
      agents: {},
      services: {},
      flows: {},
      responses: {},
      reconciliations: {},
      actions: {},
      receipts: {},
      errors: [],
      contextSummaries: {},
      challenges: {},
      contextRequests: {},
    });
    if (isNative && config.transport_mode === 'remote' && !get().technician) {
      set({
        ready: true,
        feed: {
          event_type: 'alice.feed_status',
          state: 'unavailable',
          last_success_at: null,
          message: 'Sign in to connect to the authoritative runtime',
        },
      });
      return;
    }
    transport =
      config.transport_mode === 'mock'
        ? new MockAliceTransport(scenario)
        : new RemoteAliceTransport();
    const stop = await transport.connect(
      (event) => {
        if (generation === epoch) get().ingest(event);
      },
      (message) => {
        if (generation === epoch) {
          get().error(message);
          if (
            isNative &&
            config.transport_mode === 'remote' &&
            /Technician authentication required|Technician is disabled|TECHNICIAN_SESSION_CHANGED|Technician session changed/.test(
              message,
            )
          )
            get().setTechnician(undefined);
        }
      },
    );
    if (generation !== epoch) {
      stop();
      return;
    }
    disconnect = stop;
    await Promise.all(persistence.values()).catch(() => {});
    if (isNative && config.transport_mode === 'mock' && config.biometric_mode === 'mock') {
      const technician = await nativeCall<Technician>('demo_session');
      set({ technician });
      await get().hydrate();
    } else if (isNative && get().technician) {
      await get().hydrate();
    } else if (!isNative && config.transport_mode === 'mock')
      set({
        technician: {
          technician_id: 'TECH-DEMO',
          username: 'alex.demo',
          display_name: 'Alex Morgan',
          role: 'Technician',
          enabled: true,
          enrolled: true,
        },
      });
    set({ ready: true });
    await get().refreshLLM();
  },
  refreshLLM: async () => {
    try {
      set({
        llm:
          get().scenario === '10_llm_offline'
            ? { status: 'OFFLINE', model: 'Unavailable (scenario)' }
            : await llm.health(),
      });
    } catch (err) {
      set({ llm: { status: 'OFFLINE', model: 'Unavailable' } });
      get().error(`Local language gateway unavailable: ${String(err)}`);
    }
  },
  act: async (action, verification, decisionId) => {
    const s = get(),
      d = s.decisions[decisionId ?? s.selectedId];
    if (s.mode === 'remote')
      throw new Error('Remote technician actions are unavailable; no response was delivered');
    if (!d || !s.technician)
      throw new Error('An authenticated technician and a decision are required.');
    if (s.latestDecisionByRequest[d.request.request_id] !== d.decision_id)
      throw new Error(
        'Historical assessment cannot receive actions. Select the current assessment.',
      );
    if (action !== 'APPROVE_ONCE' && !canReview(s.flows[d.decision_id] ?? 'IDLE'))
      throw new Error('Decision is not available for technician review.');
    if (
      s.actions[d.decision_id]?.action === 'APPROVE_ONCE' ||
      s.actions[d.decision_id]?.action === 'REJECT'
    )
      throw new Error('This request already has a final technician submission.');
    const command = makeAction(d, s.technician.technician_id, action, s.mode, verification);
    await persistence.get(d.decision_id);
    if (get().latestDecisionByRequest[d.request.request_id] !== d.decision_id)
      throw new Error(
        'Assessment was superseded before submission. Review the current assessment.',
      );
    get().log(
      `TECHNICIAN_${action === 'APPROVE_ONCE' ? 'APPROVAL_REQUEST' : action}`,
      `${action} requested`,
      d.decision_id,
    );
    const receipt = await transport.submitTechnicianAction(command);
    if (receipt.action_id !== command.action_id)
      throw new Error('Receipt belongs to a different action. Submission remains unconfirmed.');
    if (receipt.status === 'REJECTED') throw new Error(receipt.message);
    const event = action === 'APPROVE_ONCE' ? 'SUBMIT' : action;
    // A native action accepted before supersession can return after the new event.
    // Retain that historical receipt without reactivating the previous workflow.
    if (get().flows[d.decision_id] !== 'SUPERSEDED') get().advance(event, d.decision_id);
    set((s) => ({
      actions: { ...s.actions, [d.decision_id]: command },
      receipts: { ...s.receipts, [d.decision_id]: receipt },
    }));
    get().log(
      'ACTION_SUBMITTED',
      `${action} · ${receipt.status} · not executed by console`,
      d.decision_id,
    );
  },
  ask: async (text) => {
    const s = get(),
      d = s.decisions[s.selectedId];
    if (!d) throw new Error('Select a decision first.');
    if (s.llm.status !== 'READY')
      return `Local language gateway is offline. The structured record shows ${d.decision.result}: ${d.policy.rule_description} ${d.evidence.verified} evidence reference(s) verified; ${d.evidence.pending_external_verification} pending external verification. Use the evidence workspace to continue review.`;
    const intent = await llm.parseTechnicianIntent({ decision_id: d.decision_id, text });
    if (intent.intent === 'UNKNOWN')
      return 'Use the explicit technician action controls for approvals and rejections. Language assistance cannot authorize actions.';
    if (intent.intent === 'REQUEST_CLARIFICATION') {
      await transport.requestClarification(await llm.createAgentClarification(d));
      get().log('CLARIFICATION_SENT', 'Technician requested additional context', d.decision_id);
      return 'Additional clarification requested from the agent.';
    }
    const reply = await llm.explainDecision(d, text);
    return reply.summary;
  },
  requestContext: async (decisionId) => {
    const s = get(),
      id = decisionId ?? s.selectedId,
      d = s.decisions[id];
    // A deliberate technician context request is separate from the automatic
    // reassessment path. It issues Record 1 (CONTEXT_REQUESTED) and asks the
    // agent for a claim; the returned response still parks the flow at
    // REASSESSMENT_PENDING and only a fresh upstream decision changes the result.
    if (s.mode === 'remote')
      throw new Error('Remote context requests are unavailable; the runtime feed is read-only.');
    if (!d || !s.technician)
      throw new Error('An authenticated technician and a decision are required.');
    if (s.latestDecisionByRequest[d.request.request_id] !== d.decision_id)
      throw new Error(
        'Historical assessment cannot request context. Select the current assessment.',
      );
    if (d.decision.result !== 'HOLD' || d.policy.result === 'DENY' || !d.context_challenge.required)
      throw new Error('Additional context is only available for a HOLD that requires it.');
    if (s.responses[d.decision_id])
      throw new Error('The agent has already returned context for this assessment.');
    if (s.contextRequests[d.decision_id])
      throw new Error('A context request is already in flight for this assessment.');
    // Reuse the challenge id the auto-context path already tracked (or the one
    // named on the decision) so the returned response binds to this assessment.
    const challengeId =
      s.challenges[d.decision_id] ?? d.context_challenge.challenge_id ?? crypto.randomUUID();
    const challenge = { ...deterministicClarification(d), challenge_id: challengeId };
    set((st) => ({
      challenges: { ...st.challenges, [d.decision_id]: challengeId },
      contextRequests: { ...st.contextRequests, [d.decision_id]: challengeId },
    }));
    // Record 1: the audited fact that the technician asked for more context.
    get().log('CONTEXT_REQUESTED', 'Technician requested additional context', d.decision_id);
    try {
      await transport.requestClarification(challenge);
    } catch (err) {
      // Roll the marker back so the control returns rather than sticking "in flight".
      set((st) => {
        const next = { ...st.contextRequests };
        delete next[d.decision_id];
        return { contextRequests: next };
      });
      throw err instanceof Error ? err : new Error(String(err));
    }
  },
}));
