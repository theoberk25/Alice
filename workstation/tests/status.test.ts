import { expect, it } from 'vitest';
import { toneFor } from '@alice/ui';
it('never renders unverified evidence or disconnected infrastructure as healthy', () => {
  expect(toneFor('UNVERIFIED')).toBe('warning');
  expect(toneFor('DISCONNECTED')).toBe('neutral');
  expect(toneFor('PENDING_EXTERNAL_VERIFICATION')).toBe('warning');
  expect(toneFor('VERIFIED_LOCAL')).toBe('healthy');
});
