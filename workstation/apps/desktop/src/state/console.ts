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
export interface AuditEvent {
  id: string;
  timestamp: string;
  type: string;
  decision_id?: string;
  request_id?: string;
  detail: string;
}
export interface Technician {
  technician_id: string;
  username: string;
  display_name: string;
  role: string;
  enabled: boolean;
  enrolled: boolean;
}
interface ConsoleState {
  ready: boolean;
  mode: 'mock' | 'remote';
  biometricMode: 'mock' | 'arcface';
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
  refreshLLM: () => Promise<void>;
}
let transport: AliceTransport;
let disconnect: (() => void) | undefined;
let epoch = 0;
const llm = new OllamaProvider();
const persistence = new Map<string, Promise<void>>();
export const useConsole = create<ConsoleState>((set, get) => ({
  ready: false,
  mode: 'mock',
  biometricMode: 'mock',
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
    if (technician && isNative)
      void get()
        .hydrate()
        .catch((e) => get().error(`History could not be restored: ${String(e)}`));
  },
  hydrate: async () => {
    if (!isNative) return;
    get().restoreHistory(await nativeCall('read_console_history'));
  },
  restoreHistory: (input) => {
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
    epoch++;
    persistence.clear();
    const config = await runtimeConfig();
    if (isNative && config.transport_mode === 'mock' && reset)
      await nativeCall('reset_mock_scenario');
    set({
      ready: false,
      mode: config.transport_mode,
      biometricMode: config.biometric_mode,
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
    });
    transport =
      config.transport_mode === 'mock'
        ? new MockAliceTransport(scenario)
        : new RemoteAliceTransport();
    disconnect = await transport.connect(get().ingest, get().error);
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
}));
