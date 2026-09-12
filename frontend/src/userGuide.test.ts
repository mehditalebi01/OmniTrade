import { describe, expect, it } from 'vitest';
import { guideTopics } from './userGuide';

describe('user guide topics', () => {
  it('provides full steps for every visible index and contains no professor-only content', () => {
    expect(guideTopics).toHaveLength(9);
    expect(guideTopics.every(topic => topic.steps.length >= 3)).toBe(true);
    expect(JSON.stringify(guideTopics).toLowerCase()).not.toContain('professor');
  });
});
