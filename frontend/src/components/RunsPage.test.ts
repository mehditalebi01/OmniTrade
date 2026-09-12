import {describe,expect,it} from 'vitest';
import {canCancel,canPause,canResume} from './RunsPage';

describe('run recovery controls',()=>{
  it('offers pause only for active work',()=>{
    expect(canPause('running')).toBe(true);
    expect(canPause('paused')).toBe(false);
  });

  it('offers resume for every recoverable state',()=>{
    expect(['paused','failed','interrupted'].every(canResume)).toBe(true);
    expect(canResume('cancelled')).toBe(false);
  });

  it('keeps cancel separate and final',()=>{
    expect(canCancel('paused')).toBe(true);
    expect(canCancel('cancelled')).toBe(false);
  });
});
