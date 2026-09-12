import {useCallback,useEffect,useState} from 'react';
import {Alert,Box,Button,Card,Chip,CircularProgress,Divider,LinearProgress,Stack,Typography} from '@mui/material';
import {cancelRun,getLineage,getRun,listRuns,pauseRun,resumeRun} from '../api';
import type {Run} from '../types';

const activeStatuses=['queued','running','pausing','cancelling'];
export const canPause=(status:string)=>['queued','running'].includes(status);
export const canResume=(status:string)=>['paused','failed','interrupted'].includes(status);
export const canCancel=(status:string)=>['queued','running','pausing','paused'].includes(status);

function statusColor(status:string):'success'|'warning'|'error'|'info'|'default'{
  if(status==='succeeded')return 'success';
  if(['degraded','pausing','paused'].includes(status))return 'warning';
  if(['failed','interrupted','cancelled'].includes(status))return 'error';
  if(['queued','running','cancelling'].includes(status))return 'info';
  return 'default';
}

export default function RunsPage({focusId,onOpenReport}:{focusId?:string;onOpenReport:(id:string)=>void}){
  const[runs,setRuns]=useState<Run[]>([]);
  const[selected,setSelected]=useState<Run>();
  const[lineage,setLineage]=useState<Record<string,unknown>>({});
  const[busy,setBusy]=useState(true);
  const[action,setAction]=useState('');
  const[message,setMessage]=useState('');
  const[error,setError]=useState('');
  const replaceRun=(run:Run)=>{setSelected(run);setRuns(current=>current.map(item=>item.id===run.id?run:item));};
  const load=useCallback(async()=>{
    try{const items=await listRuns();setRuns(items);setSelected(current=>items.find(run=>run.id===(focusId??current?.id))??items[0]);setError('');}
    catch(reason){setError(String(reason));}
    finally{setBusy(false);}
  },[focusId]);
  useEffect(()=>{void load();},[load]);
  useEffect(()=>{
    if(!selected||!activeStatuses.includes(selected.status))return;
    const timer=setInterval(async()=>{try{replaceRun(await getRun(selected.id));}catch(reason){setError(String(reason));}},800);
    return()=>clearInterval(timer);
  },[selected?.id,selected?.status]);

  async function control(kind:'pause'|'resume'|'cancel'){
    if(!selected)return;
    setAction(kind);setError('');setMessage('');
    try{
      const run=kind==='pause'?await pauseRun(selected.id):kind==='resume'?await resumeRun(selected.id):await cancelRun(selected.id);
      replaceRun(run);
      setMessage(kind==='pause'?'Pause requested. The current node batch will finish before the checkpoint is saved.':kind==='resume'?'Resume started from the latest durable checkpoint.':'Cancellation requested.');
    }catch(reason){setError(String(reason));}
    finally{setAction('');}
  }

  if(busy)return <CircularProgress/>;
  return <Stack spacing={2}>
    <Box><Typography variant="h4" fontWeight={900}>Run History</Typography><Typography color="text.secondary">Pause active work, continue saved work, or inspect any analysis run.</Typography></Box>
    <Alert severity="info">Paused, failed, and interrupted runs can continue from their latest checkpoint. For an old live run, reconnect its saved data and AI providers first.</Alert>
    {error&&<Alert severity="error">{error}</Alert>}{message&&<Alert severity="success">{message}</Alert>}
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'340px 1fr'},gap:2}}>
      <Card sx={{maxHeight:'70vh',overflow:'auto'}}>{runs.length?runs.map(run=><Box key={run.id} onClick={()=>{setSelected(run);setLineage({});setMessage('');}} sx={{p:2,cursor:'pointer',background:selected?.id===run.id?'#172743':'transparent'}}><Stack direction="row" justifyContent="space-between"><Typography fontWeight={800}>{run.ticker}</Typography><Chip size="small" label={run.status} color={statusColor(run.status)}/></Stack><Typography variant="caption">{new Date(run.created_at).toLocaleString()}</Typography><Divider sx={{mt:1.5}}/></Box>):<Alert severity="info">No runs yet.</Alert>}</Card>
      <Card sx={{p:3}}>{selected?<Stack spacing={2}>
        <Stack direction={{xs:'column',sm:'row'}} justifyContent="space-between" gap={1}><Box><Typography variant="h5" fontWeight={800}>{selected.ticker} analysis</Typography><Typography color="text.secondary" sx={{overflowWrap:'anywhere'}}>Trace {selected.trace_id}</Typography></Box><Chip label={selected.status} color={statusColor(selected.status)}/></Stack>
        {activeStatuses.includes(selected.status)&&<LinearProgress/>}
        {selected.status==='paused'&&<Alert severity="warning">This run is safely paused. Completed nodes are saved and will not run again.</Alert>}
        <Typography>Created: {new Date(selected.created_at).toLocaleString()}</Typography><Typography>As of: {new Date(selected.as_of).toLocaleString()}</Typography><Typography>Analysts: {selected.configuration.analysts.join(', ')}</Typography><Typography>Risk: {selected.configuration.risk_profile} · Depth: {selected.configuration.research_depth}</Typography>
        {selected.degraded_reasons.map(reason=><Alert severity="warning" key={reason}>{reason}</Alert>)}
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
          <Button variant="outlined" disabled={!canPause(selected.status)||Boolean(action)} onClick={()=>void control('pause')}>Pause safely</Button>
          <Button variant="contained" disabled={!canResume(selected.status)||Boolean(action)} onClick={()=>void control('resume')}>Resume from checkpoint</Button>
          <Button color="error" variant="outlined" disabled={!canCancel(selected.status)||Boolean(action)} onClick={()=>void control('cancel')}>Cancel</Button>
          <Button onClick={async()=>{try{setLineage(await getLineage(selected.id));}catch(reason){setError(String(reason));}}}>Inspect checkpoint</Button>
          <Button variant="contained" color="secondary" disabled={!['succeeded','degraded'].includes(selected.status)} onClick={()=>onOpenReport(selected.id)}>Open report</Button>
        </Stack>
        {Object.keys(lineage).length>0&&<Box component="pre" sx={{fontSize:11,whiteSpace:'pre-wrap',background:'#08101f',p:2,borderRadius:1,maxHeight:300,overflow:'auto'}}>{JSON.stringify(lineage,null,2)}</Box>}
      </Stack>:<Alert severity="info">Select a run.</Alert>}</Card>
    </Box>
  </Stack>;
}
