import { writeFileSync, readFileSync } from 'node:fs';
import { z } from 'zod';
import { AliceEventSchema, AgentStatusSchema } from '../packages/contracts/src/alice/events';
import {
  TechnicianActionSchema,
  ClarificationSchema,
} from '../packages/contracts/src/alice/commands';
import { normalizeEvent } from '../packages/contracts/src/adapters/legacy';
import { demoAgent, reassessedDecision } from '../fixtures/scenarios';
for (const [name, schema] of Object.entries({
  'alice-events': AliceEventSchema,
  'technician-action': TechnicianActionSchema,
  'context-request': ClarificationSchema,
  'agent-status': AgentStatusSchema,
})) {
  writeFileSync(
    `docs/contracts/${name}.schema.json`,
    JSON.stringify(z.toJSONSchema(schema), null, 2) + '\n',
  );
}
for (const name of ['decision', 'status', 'reconciliation']) {
  writeFileSync(
    `fixtures/alice/${name}.json`,
    JSON.stringify(
      normalizeEvent(JSON.parse(readFileSync(`fixtures/legacy/${name}.json`, 'utf8'))),
      null,
      2,
    ) + '\n',
  );
}
writeFileSync('fixtures/alice/agent-status.json', JSON.stringify(demoAgent(), null, 2) + '\n');
writeFileSync(
  'fixtures/alice/reassessment.json',
  JSON.stringify(reassessedDecision(), null, 2) + '\n',
);
