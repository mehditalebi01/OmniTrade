import{beforeEach,describe,expect,it,vi}from'vitest';

function jwt(exp:number):string{
  return `header.${btoa(JSON.stringify({exp})).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_')}.signature`;
}

describe('authentication lifecycle',()=>{
  beforeEach(()=>{localStorage.clear();vi.resetModules();vi.restoreAllMocks()});

  it('rejects and removes an expired saved token',async()=>{
    localStorage.setItem('omnitrade-token',jwt(Math.floor(Date.now()/1000)-60));
    const{hasToken}=await import('./api');
    expect(hasToken()).toBe(false);
    expect(localStorage.getItem('omnitrade-token')).toBeNull();
  });

  it('clears the session and sends an event after an authenticated 401',async()=>{
    localStorage.setItem('omnitrade-token',jwt(Math.floor(Date.now()/1000)+3600));
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Invalid or expired token'}),{status:401,headers:{'Content-Type':'application/json'}})));
    const{AUTH_EXPIRED_EVENT,listRuns}=await import('./api');
    const expired=vi.fn();window.addEventListener(AUTH_EXPIRED_EVENT,expired);
    await expect(listRuns()).rejects.toThrow('Invalid or expired token');
    expect(localStorage.getItem('omnitrade-token')).toBeNull();
    expect(expired).toHaveBeenCalledOnce();
  });
});
