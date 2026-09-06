import type {
  RuntimeReview,
  RuntimeReviewReceipt,
  RuntimeSubmission,
  RuntimeReviewStatus,
} from '@alice/contracts';
import type { RuntimeRequest } from './runtime-feed';
export interface RuntimeReviewer {
  readonly available: boolean;
  read(requestId: string): Promise<RuntimeReview>;
  submit(verificationId: string): Promise<RuntimeReviewReceipt>;
  readSubmission(requestId: string): Promise<RuntimeSubmission | null>;
  reconcile(requestId: string): Promise<RuntimeSubmission>;
  status(): Promise<RuntimeReviewStatus>;
}
/** Display eligibility only. Native and Pi independently enforce every binding. */
export function matchesRuntimeRequest(snapshot: RuntimeReview, request?: RuntimeRequest): boolean {
  return (
    !!request &&
    snapshot.request_id === request.id &&
    snapshot.request_sha256 === request.events[0]?.correlation.request_sha256 &&
    snapshot.decision_event_id === request.decision?.event_id &&
    snapshot.decision_event_hash === request.decision?.event_hash
  );
}
export function runtimeReviewBinding(snapshot: RuntimeReview): string {
  return JSON.stringify([
    snapshot.request_id,
    snapshot.request_sha256,
    snapshot.decision_event_id,
    snapshot.decision_event_hash,
    snapshot.release_sha256,
    snapshot.authority_interval_ref,
    snapshot.runtime_epoch,
    snapshot.review_nonce,
  ]);
}
