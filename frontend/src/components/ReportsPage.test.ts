import { describe, expect, it } from 'vitest';
import type { DebateCase } from '../types';
import { debateSupport } from './ReportsPage';

const baseCase: DebateCase = {
  agent: 'Bull Researcher',
  stance: 'BULLISH',
  confidence: 0.64,
  summary: 'Evidence supports the case.',
  key_points: [],
  counterpoints: [],
};

describe('debateSupport', () => {
  it('shows the separate directional support for new reports', () => {
    expect(debateSupport({ ...baseCase, support: 0.72 })).toBe(0.72);
  });

  it('keeps older saved reports readable', () => {
    expect(debateSupport(baseCase)).toBe(baseCase.confidence);
  });
});
