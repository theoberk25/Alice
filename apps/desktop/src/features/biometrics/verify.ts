import {
  VerificationSchema,
  LiveBiometricSessionSchema,
  LiveBiometricPreviewSchema,
  type BiometricIntent,
  type Verification,
} from '@alice/contracts';
import type { IdentityClaim } from '@alice/domain';
import { nativeCall, isNative } from '../../lib/native';
export async function verifyFace(
  claim: IdentityClaim,
  _frames: string[],
  mockResult?: 'PASS' | 'FAIL',
): Promise<Verification> {
  if (!mockResult)
    throw new Error('Renderer image authentication is retired. Begin a native biometric session.');
  if (isNative)
    return VerificationSchema.parse(
      await nativeCall('mock_verify', {
        ...claim,
        result: mockResult,
      }),
    );
  return VerificationSchema.parse({
    ...claim,
    verification_id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    expires_at: new Date(Date.now() + 60_000).toISOString(),
    result: mockResult,
    provider: 'mock',
  });
}
export async function beginBiometricSession(intent: BiometricIntent) {
  return LiveBiometricSessionSchema.parse(await nativeCall('begin_biometric_session', { intent }));
}
export async function readBiometricSession(sessionId: string) {
  return LiveBiometricSessionSchema.parse(
    await nativeCall('read_biometric_session', { sessionId }),
  );
}
export async function readBiometricPreview(sessionId: string) {
  return LiveBiometricPreviewSchema.nullable().parse(
    await nativeCall('read_biometric_preview', { sessionId }),
  );
}
export async function cancelBiometricSession(sessionId: string) {
  await nativeCall('cancel_biometric_session', { sessionId });
}
export async function recoverBiometricEnrollment(technicianId: string) {
  await nativeCall('recover_face_enrollment', { technicianId });
}
