import type { Verification } from '@alice/contracts';
export interface IdentityClaim {
  technician_id: string;
  decision_id: string;
  request_id: string;
}
export interface BiometricVerifier {
  verifyIdentity(claim: IdentityClaim, frames: string[]): Promise<Verification>;
  verifyAuthenticity?(frames: string[]): Promise<{ result: 'PASS' | 'FAIL' | 'NOT_CONFIGURED' }>;
}
