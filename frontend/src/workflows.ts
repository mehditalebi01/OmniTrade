import type { WorkflowRecord } from './types';

/** The Workflow Lab owns one active draft. New Analysis runs its latest publication. */
export function activeWorkflow(items: WorkflowRecord[]): WorkflowRecord | undefined {
  return [...items].sort((left, right) => {
    const publicationOrder = Number(Boolean(right.published_version_id)) - Number(Boolean(left.published_version_id));
    return right.version - left.version || publicationOrder || left.id.localeCompare(right.id);
  })[0];
}
