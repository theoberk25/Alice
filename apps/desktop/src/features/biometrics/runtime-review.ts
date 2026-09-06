import {
  RuntimeReviewSchema,
  RuntimeReviewReceiptSchema,
  RuntimeSubmissionSchema,
  RuntimeReviewStatusSchema,
} from '@alice/contracts';
import type { RuntimeReviewer } from '@alice/domain';
import { isNative, nativeCall } from '../../lib/native';
export const runtimeReviewer: RuntimeReviewer = {
  available: isNative,
  async status() {
    return RuntimeReviewStatusSchema.parse(await nativeCall('runtime_review_status'));
  },
  async read(requestId) {
    const snapshot = RuntimeReviewSchema.parse(
      await nativeCall('read_runtime_review', { requestId }),
    );
    if (snapshot.request_id !== requestId) throw new Error('Runtime request identity changed');
    return snapshot;
  },
  async submit(verificationId) {
    return RuntimeReviewReceiptSchema.parse(
      await nativeCall('submit_runtime_review', { verificationId }),
    );
  },
  async readSubmission(requestId) {
    const submission = RuntimeSubmissionSchema.nullable().parse(
      await nativeCall('read_runtime_submission', { requestId }),
    );
    if (submission && submission.request_id !== requestId)
      throw new Error('Submission identity changed');
    return submission;
  },
  async reconcile(requestId) {
    const submission = RuntimeSubmissionSchema.parse(
      await nativeCall('reconcile_runtime_submission', { requestId }),
    );
    if (submission.request_id !== requestId) throw new Error('Submission identity changed');
    return submission;
  },
};
