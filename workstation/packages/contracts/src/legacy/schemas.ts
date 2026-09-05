import { z } from 'zod';
import { DecisionSchema, StatusSchema, ReconciliationSchema } from '../alice/events';
export const LegacyDecisionSchema = DecisionSchema.extend({
  event_type: z.literal('dcamr.decision'),
  system: DecisionSchema.shape.system
    .omit({ node: true })
    .extend({ dcamr_node: z.string().min(1) }),
});
export const LegacyStatusSchema = StatusSchema.omit({ node: true }).extend({
  event_type: z.literal('dcamr.status'),
  dcamr_node: z.string().min(1),
});
export const LegacyReconciliationSchema = ReconciliationSchema.extend({
  event_type: z.literal('dcamr.reconciliation'),
});
export const LegacyEventSchema = z.discriminatedUnion('event_type', [
  LegacyDecisionSchema,
  LegacyStatusSchema,
  LegacyReconciliationSchema,
]);
