import { AliceEventSchema, type AliceEvent } from '../alice/events';
import { LegacyEventSchema } from '../legacy/schemas';
// Only known legacy node prefixes are translated; identifiers otherwise stay intact.
const nodeName = (node: string) => node.replace(/^DCAMR-/i, 'ALICE-');
export function normalizeEvent(input: unknown): AliceEvent {
  const legacy = LegacyEventSchema.safeParse(input);
  if (!legacy.success) return AliceEventSchema.parse(input);
  const e = legacy.data;
  if (e.event_type === 'dcamr.decision') {
    const { dcamr_node, ...system } = e.system;
    return AliceEventSchema.parse({
      ...e,
      event_type: 'alice.decision',
      system: { ...system, node: nodeName(dcamr_node) },
    });
  }
  if (e.event_type === 'dcamr.status') {
    const { dcamr_node, ...rest } = e;
    return AliceEventSchema.parse({
      ...rest,
      event_type: 'alice.status',
      node: nodeName(dcamr_node),
    });
  }
  return AliceEventSchema.parse({ ...e, event_type: 'alice.reconciliation' });
}
