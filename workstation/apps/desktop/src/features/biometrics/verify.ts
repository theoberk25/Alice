import { VerificationSchema, type Verification } from '@alice/contracts';
import type { IdentityClaim } from '@alice/domain';
import { nativeCall, isNative } from '../../lib/native';
export async function verifyFace(
  claim: IdentityClaim,
  frames: string[],
  mockResult?: 'PASS' | 'FAIL',
): Promise<Verification> {
  if (isNative)
    return VerificationSchema.parse(
      await nativeCall(mockResult ? 'mock_verify' : 'verify_face', {
        ...claim,
        frames,
        result: mockResult,
      }),
    );
  if (!mockResult) throw new Error('Real facial verification requires ALICE.app.');
  return VerificationSchema.parse({
    ...claim,
    verification_id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    expires_at: new Date(Date.now() + 60_000).toISOString(),
    result: mockResult,
    provider: 'mock',
  });
}
