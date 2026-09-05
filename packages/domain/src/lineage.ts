import type { Decision } from '@alice/contracts';

export interface DecisionIndexes {
  requestDecisionHistory: Record<string, string[]>;
  latestDecisionByRequest: Record<string, string>;
}

// A request has one immutable, linear assessment chain. Time/order of a cached
// query is not authority; only validated parent/root/sequence determine order.
export function indexDecision(
  decisions: Record<string, Decision>,
  indexes: DecisionIndexes,
  next: Decision,
): DecisionIndexes {
  const request = next.request.request_id;
  const history = indexes.requestDecisionHistory[request] ?? [];
  const lineage = next.reassessment;
  if (lineage) {
    const previous = decisions[lineage.previous_decision_id];
    if (!previous) throw new Error('Reassessment previous decision is unknown.');
    for (const field of ['request_id', 'agent_id', 'mission_id', 'action', 'target'] as const)
      if (next.request[field] !== previous.request[field])
        throw new Error(`Reassessment changed request.${field}; submit a new request instead.`);
    const root = previous.reassessment?.root_decision_id ?? previous.decision_id;
    if (lineage.root_decision_id !== root || !decisions[root] || decisions[root]?.reassessment)
      throw new Error('Incorrect reassessment root lineage.');
    if (lineage.sequence !== (previous.reassessment?.sequence ?? 0) + 1)
      throw new Error('Reassessment sequence must immediately follow its parent.');
    if (indexes.latestDecisionByRequest[request] !== previous.decision_id)
      throw new Error(
        'Reassessment must extend the current assessment; branches are not supported.',
      );
    if (next.decision_id === previous.decision_id || next.decision_id === root)
      throw new Error('Reassessment requires a new decision ID.');
  } else if (history.length) {
    throw new Error(
      'Request already has an original assessment; explicit reassessment lineage required.',
    );
  }
  return {
    requestDecisionHistory: {
      ...indexes.requestDecisionHistory,
      [request]: [...history, next.decision_id],
    },
    latestDecisionByRequest: { ...indexes.latestDecisionByRequest, [request]: next.decision_id },
  };
}

export function rebuildDecisionIndexes(decisions: Record<string, Decision>): DecisionIndexes {
  const known: Record<string, Decision> = {};
  let indexes: DecisionIndexes = { requestDecisionHistory: {}, latestDecisionByRequest: {} };
  for (const decision of Object.values(decisions).sort(
    (a, b) =>
      (a.reassessment?.sequence ?? 0) - (b.reassessment?.sequence ?? 0) ||
      a.decision_id.localeCompare(b.decision_id),
  )) {
    indexes = indexDecision(known, indexes, decision);
    known[decision.decision_id] = decision;
  }
  return indexes;
}
