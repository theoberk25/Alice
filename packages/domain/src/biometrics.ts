import type { BiometricIntent, LiveBiometricSession } from '@alice/contracts';
export interface IdentityClaim {
  technician_id: string;
  decision_id: string;
  request_id: string;
}
export interface BiometricVerifier {
  begin(intent: BiometricIntent): Promise<LiveBiometricSession>;
  read(sessionId: string): Promise<LiveBiometricSession>;
  cancel(sessionId: string): Promise<void>;
}
