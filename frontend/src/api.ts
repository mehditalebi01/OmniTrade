import type{AnalysisOptions,Budget,CatalogSuggestion,ReportData,ReportSummary,Run,RunActivity,RunConfiguration,UserProfile,ValidationResult,WorkflowRecord}from'./types';

const API='/api/v1';
const TOKEN_KEY='omnitrade-token';
export const AUTH_EXPIRED_EVENT='omnitrade-auth-expired';
let token=localStorage.getItem(TOKEN_KEY)??'';

function tokenHasExpired(value:string):boolean{
  try{
    const encoded=value.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');
    const payload=JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length/4)*4,'=')))as{exp?:number};
    return typeof payload.exp!=='number'||payload.exp*1000<=Date.now();
  }catch{return true}
}

function clearSession(notify:boolean):void{
  token='';
  localStorage.removeItem(TOKEN_KEY);
  if(notify)window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

export function formatApiErrorDetail(detail:unknown):string{
  if(typeof detail==='string')return detail;
  if(Array.isArray(detail))return detail.map(item=>formatApiErrorDetail(item)).filter(Boolean).join('; ');
  if(detail&&typeof detail==='object'){
    const value=detail as Record<string,unknown>;
    if(typeof value.msg==='string'){
      const location=Array.isArray(value.loc)?value.loc.filter(part=>part!=='body').join(' › '):'';
      return location?`${location}: ${value.msg}`:value.msg;
    }
    const message=typeof value.message==='string'?value.message:'';
    const validation=value.validation&&typeof value.validation==='object'
      ?(value.validation as Record<string,unknown>).errors:undefined;
    const validationText=validation?formatApiErrorDetail(validation):'';
    if(message&&validationText)return `${message}: ${validationText}`;
    if(message)return message;
    try{return JSON.stringify(detail)}catch{return 'Request failed'}
  }
  return detail==null?'Request failed':String(detail);
}

async function errorMessage(response:Response):Promise<string>{
  const text=await response.text();
  try{
    const body=JSON.parse(text) as {detail?:unknown};
    return formatApiErrorDetail(body.detail??body);
  }catch{return text||`Request failed: ${response.status}`}
}

async function request<T>(path:string,options:RequestInit={}):Promise<T>{
  const authenticated=Boolean(token)&&path!=='/auth/login';
  const response=await fetch(`${API}${path}`,{...options,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{}) ,...options.headers}});
  if(response.status===401&&authenticated)clearSession(true);
  if(!response.ok)throw new Error(await errorMessage(response));
  return response.status===204?undefined as T:response.json();
}

export async function login(username:string,password:string){
  const data=await request<{access_token:string}>('/auth/login',{method:'POST',body:JSON.stringify({username,password})});
  token=data.access_token;
  localStorage.setItem(TOKEN_KEY,token);
  return data;
}

export function hasToken():boolean{
  if(!token||tokenHasExpired(token)){
    if(token)clearSession(false);
    return false;
  }
  return true;
}

export const logout=()=>clearSession(false);
export const listWorkflows=()=>request<WorkflowRecord[]>('/workflows');
export const createSample=()=>request<WorkflowRecord>('/workflows/sample',{method:'POST'});
export const validateWorkflow=(id:string)=>request<ValidationResult>(`/workflows/${id}/validate`,{method:'POST'});
export const publishWorkflow=(id:string)=>request<{id:string}>(`/workflows/${id}/publish`,{method:'POST'});
export const updateWorkflow=(id:string,definition:WorkflowRecord['definition'])=>request<WorkflowRecord>(`/workflows/${id}`,{method:'PUT',body:JSON.stringify(definition)});
export const resetWorkflowDefault=(id:string)=>request<WorkflowRecord>(`/workflows/${id}/reset-default`,{method:'POST'});
export const createRun=(workflow_version_id:string,ticker:string,as_of:string,configuration:RunConfiguration,budget_override:Budget)=>request<Run>('/runs',{method:'POST',body:JSON.stringify({workflow_version_id,ticker,as_of,configuration,budget_override})});
export const listRuns=()=>request<Run[]>('/runs');
export const getRun=(id:string)=>request<Run>(`/runs/${id}`);
export const pauseRun=(id:string)=>request<Run>(`/runs/${id}/pause`,{method:'POST'});
export const cancelRun=(id:string)=>request<Run>(`/runs/${id}/cancel`,{method:'POST'});
export const resumeRun=(id:string)=>request<Run>(`/runs/${id}/resume`,{method:'POST'});
export const getLineage=(id:string)=>request<Record<string,unknown>>(`/runs/${id}/lineage`);
export const getActivity=(id:string)=>request<RunActivity>(`/runs/${id}/activity`);
export const listReports=()=>request<ReportSummary[]>('/report-history');
export const getReport=(id:string)=>request<ReportData>(`/reports/${id}`);
export async function downloadReport(id:string,format:string){
  const response=await fetch(`${API}/reports/${id}/export/${format}`,{headers:{Authorization:`Bearer ${token}`}});
  if(response.status===401)clearSession(true);
  if(!response.ok)throw new Error(await errorMessage(response));
  const blob=await response.blob();const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`omnitrade-${id}.${format}`;link.click();URL.revokeObjectURL(url);
}
export const getProfile=()=>request<UserProfile>('/profile');
export const saveProfile=(profile:UserProfile)=>request<UserProfile>('/profile',{method:'PUT',body:JSON.stringify(profile)});
export const getAnalysisOptions=()=>request<AnalysisOptions>('/analysis-options');
export const getCatalog=()=>request<{count:number;nodes:Record<string,{group:string;description:string;inputs:Record<string,string>;outputs:Record<string,string>;suggested_targets:CatalogSuggestion[]}>}>('/catalog');
export const getConnectionCatalog=()=>request<{providers:Record<string,import('./types').ConnectionSpec>}>('/connections/catalog');
export const listConnections=()=>request<import('./types').ConnectionStatus[]>('/connections');
export const saveConnection=(provider:string,value:import('./types').ConnectionInput)=>request<import('./types').ConnectionStatus>(`/connections/${provider}`,{method:'PUT',body:JSON.stringify(value)});
export const verifyConnection=(provider:string)=>request<import('./types').ConnectionStatus>(`/connections/${provider}/verify`,{method:'POST'});
export const loadConnectionModels=(provider:string)=>request<{provider:string;models:string[]}>(`/connections/${provider}/models`);
export const deleteConnection=(provider:string)=>request<void>(`/connections/${provider}`,{method:'DELETE'});
