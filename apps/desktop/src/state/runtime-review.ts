import { create } from 'zustand';
import {
  RuntimeSubmissionSchema,
  type RuntimeReviewAction,
  type RuntimeSubmission,
} from '@alice/contracts';
import { runtimeReviewer } from '../features/biometrics/runtime-review';

interface ReviewState {
  submissions: Record<string, RuntimeSubmission>;
  sending: Record<string, boolean>;
  remember: (submission: RuntimeSubmission | null, requestId: string) => void;
  submit: (requestId: string, action: RuntimeReviewAction, verificationId: string) => Promise<void>;
}
/** Renderer cache only. Native SQLite is the durable submission record and authority boundary. */
export const useRuntimeReview = create<ReviewState>((set, get) => ({
  submissions: {},
  sending: {},
  remember: (submission, requestId) => {
    if (!submission) return; // A late pre-submission read cannot erase an in-flight outcome.
    RuntimeSubmissionSchema.parse(submission);
    if (submission.request_id !== requestId) throw new Error('Conflicting saved request identity');
    const current = get().submissions[requestId];
    if (current && current.action_id !== submission.action_id)
      throw new Error('Conflicting saved review action');
    if (
      current?.state === 'ACCEPTED' &&
      submission.state !== 'ACCEPTED' &&
      !['REVIEW_SUBMISSION_BINDING_CONFLICT', 'REVIEW_SUBMISSION_CURRENTNESS_UNCONFIRMED'].includes(
        submission.error ?? '',
      )
    )
      return;
    set((s) => ({ submissions: { ...s.submissions, [requestId]: submission } }));
  },
  submit: async (requestId, action, verificationId) => {
    if (get().sending[requestId] || get().submissions[requestId])
      throw new Error('This request already has a submission. Check its recorded outcome.');
    const pending: RuntimeSubmission = {
      schema_version: 'alice-native-review-submission-v1',
      request_id: requestId,
      action_id: verificationId,
      action,
      state: 'PENDING',
      created_at: new Date().toISOString(),
      receipt: null,
      error: null,
    };
    set((s) => ({
      sending: { ...s.sending, [requestId]: true },
      submissions: { ...s.submissions, [requestId]: pending },
    }));
    try {
      const receipt = await runtimeReviewer.submit(verificationId);
      get().remember(
        RuntimeSubmissionSchema.parse({ ...pending, state: 'ACCEPTED', receipt }),
        requestId,
      );
    } catch (reason) {
      // Native records BEFORE transmission. Only an authenticated native read proving
      // no record exists establishes a preflight failure; a transport error cannot.
      let persisted: RuntimeSubmission | null | undefined;
      try {
        persisted = await runtimeReviewer.readSubmission(requestId);
      } catch {
        /* retain uncertainty */
      }
      if (persisted) {
        get().remember(persisted, requestId);
        if (persisted.state === 'ACCEPTED') return;
      } else if (persisted === null) {
        set((s) => {
          const submissions = { ...s.submissions };
          delete submissions[requestId];
          return { submissions };
        });
      } else get().remember({ ...pending, state: 'UNCERTAIN', error: String(reason) }, requestId);
      throw reason;
    } finally {
      set((s) => ({ sending: { ...s.sending, [requestId]: false } }));
    }
  },
}));
