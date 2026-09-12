import { describe, expect, it } from 'vitest';
import { automaticKeylessProviders, isOptionalPublicFeed } from './ConnectionsPage';
import type { ConnectionSpec } from '../types';

function spec(label: string, autoConnect: boolean): ConnectionSpec {
  return { label, category: 'data', key_optional: true, auto_connect: autoConnect, models: [], capabilities: ['sentiment'] };
}

describe('automaticKeylessProviders', () => {
  it('does not leave unstable public feeds waiting for verification', () => {
    expect(automaticKeylessProviders({
      yfinance: spec('Yahoo Finance', true),
      polymarket: spec('Polymarket', true),
      stocktwits: spec('StockTwits', false),
      reddit: spec('Reddit', false),
    })).toEqual(['yfinance', 'polymarket']);
  });

  it('identifies public feeds that must be removed after failed verification', () => {
    expect(isOptionalPublicFeed(spec('Reddit', false))).toBe(true);
    expect(isOptionalPublicFeed(spec('Yahoo Finance', true))).toBe(false);
  });
});
