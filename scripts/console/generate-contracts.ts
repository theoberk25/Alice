import { writeFileSync, readFileSync } from 'node:fs';
import { z } from 'zod';
import { resolve } from 'node:path';
import { consoleRoot } from './paths.mjs';
import { AliceEventSchema, AgentStatusSchema } from '../../packages/contracts/src/alice/events';
import {
  TechnicianActionSchema,
  ClarificationSchema,
} from '../../packages/contracts/src/alice/commands';
import { normalizeEvent } from '../../packages/contracts/src/adapters/legacy';
import { demoAgent, reassessedDecision } from '../../fixtures/scenarios';
for (const [name, schema] of Object.entries({
  'alice-events': AliceEventSchema,
  'technician-action': TechnicianActionSchema,
  'context-request': ClarificationSchema,
  'agent-status': AgentStatusSchema,
})) {
  writeFileSync(
    resolve(consoleRoot, `docs/contracts/${name}.schema.json`),
    JSON.stringify(z.toJSONSchema(schema), null, 2) + '\n',
  );
}
for (const name of ['decision', 'status', 'reconciliation']) {
  writeFileSync(
    resolve(consoleRoot, `fixtures/alice/${name}.json`),
    JSON.stringify(
      normalizeEvent(
        JSON.parse(readFileSync(resolve(consoleRoot, `fixtures/legacy/${name}.json`), 'utf8')),
      ),
      null,
      2,
    ) + '\n',
  );
}
writeFileSync(
  resolve(consoleRoot, 'fixtures/alice/agent-status.json'),
  JSON.stringify(demoAgent(), null, 2) + '\n',
);
writeFileSync(
  resolve(consoleRoot, 'fixtures/alice/reassessment.json'),
  JSON.stringify(reassessedDecision(), null, 2) + '\n',
);
