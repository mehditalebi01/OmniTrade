import {useCallback,useEffect,useMemo,useState} from 'react';
import {Alert,Avatar,Box,Button,Card,Chip,CircularProgress,Grid,LinearProgress,MenuItem,Stack,TextField,Typography} from '@mui/material';
import {getActivity,listRuns} from '../api';
import type {Run,RunActivity,RunEvent} from '../types';

const roles=[
  ['market_analyst','Market Analyst','Technical and price evidence','M'],
  ['fundamental_analyst','Fundamental Analyst','Company value and financial health','F'],
  ['news_analyst','News Analyst','Events and market context','N'],
  ['sentiment_analyst','Sentiment Analyst','Public sentiment signals','S'],
  ['bull','Bull Researcher','Builds the positive case','B+'],
  ['bear','Bear Researcher','Challenges the positive case','B-'],
  ['aggressive','Aggressive Risk','High reward and high risk view','A'],
  ['balanced','Balanced Risk','Balanced exposure view','R'],
  ['conservative','Conservative Risk','Capital protection view','C'],
  ['decision','Portfolio Manager','Validates the final decision','PM'],
] as const;
const reportReady=['succeeded','degraded'];

export default function AgentRoom({focusId,onReport}:{focusId?:string;onReport:(id:string)=>void}){
  const[runs,setRuns]=useState<Run[]>([]);
  const[runId,setRunId]=useState(focusId??'');
  const[activity,setActivity]=useState<RunActivity>();
  const[error,setError]=useState('');
  const load=useCallback(async()=>{
    if(!runId)return;
    try{setActivity(await getActivity(runId));setError('');}
    catch(reason){setError(String(reason));}
  },[runId]);
  useEffect(()=>{void listRuns().then(items=>{setRuns(items);setRunId(current=>focusId??current??items[0]?.id??'');});},[focusId]);
  useEffect(()=>{void load();const timer=setInterval(()=>void load(),800);return()=>clearInterval(timer);},[load]);
  const status=activity?.run.status??'waiting';
  const progress=activity?Math.min(100,Math.round(activity.events.filter(event=>event.event_type==='node.succeeded'||event.event_type==='node.degraded').length/33*100)):0;
  const lastByNode=useMemo(()=>{
    const map:Record<string,RunEvent>={};
    for(const event of activity?.events??[])if(event.node_id)map[event.node_id]=event;
    return map;
  },[activity]);

  return <Stack spacing={2}>
    <Stack direction={{xs:'column',md:'row'}} justifyContent="space-between" alignItems={{md:'center'}}>
      <Box><Typography variant="h4" fontWeight={900}>Live Agent Room</Typography><Typography color="text.secondary">Real workflow events show what each agent is doing and how it affects the result.</Typography></Box>
      <TextField select size="small" label="Analysis run" value={runId} onChange={event=>setRunId(event.target.value)} sx={{minWidth:270}}>{runs.map(run=><MenuItem value={run.id} key={run.id}>{run.ticker} · {run.status} · {new Date(run.created_at).toLocaleTimeString()}</MenuItem>)}</TextField>
    </Stack>
    {error&&<Alert severity="error">{error}</Alert>}
    {!activity?<Card sx={{p:6,textAlign:'center'}}><CircularProgress/><Typography sx={{mt:2}}>Waiting for a run...</Typography></Card>:<>
      <Card className="run-command"><Stack direction={{xs:'column',sm:'row'}} justifyContent="space-between"><Box><Typography variant="h5" fontWeight={800}>{activity.run.ticker} multi-agent analysis</Typography><Typography color="text.secondary">{activity.run.configuration.analysts.join(', ')} · {activity.run.configuration.risk_profile} risk · depth {activity.run.configuration.research_depth}</Typography></Box><Chip className={status==='running'?'status-live':''} color={status==='succeeded'?'success':status==='failed'?'error':'secondary'} label={status.toUpperCase()}/></Stack><LinearProgress variant="determinate" value={progress} sx={{mt:2,height:8,borderRadius:5}}/><Typography variant="caption">{progress}% of workflow nodes completed</Typography></Card>
      {status==='paused'&&<Alert severity="warning">This run is paused at a durable checkpoint. Open Run History to resume it.</Alert>}
      {['failed','interrupted'].includes(status)&&<Alert severity="error">This run stopped before its report was ready. Open Run History to resume it.</Alert>}
      <Grid container spacing={2}>
        <Grid item xs={12} lg={8}><Grid container spacing={1.5}>{roles.map(([id,name,goal,initial])=>{const event=lastByNode[id];const state=event?.event_type.replace('node.','')??'waiting';const output=activity.nodes[id]?.output;return <Grid item xs={12} sm={6} md={4} key={id}><Card className={`agent-card agent-${state}`}><Stack direction="row" spacing={1.5}><Avatar>{initial}</Avatar><Box><Typography fontWeight={800}>{name}</Typography><Chip size="small" label={state}/></Box></Stack><Typography variant="body2" color="text.secondary" sx={{my:1.5,minHeight:40}}>{goal}</Typography><Typography variant="caption">{impact(output,state)}</Typography></Card></Grid>;})}</Grid></Grid>
        <Grid item xs={12} lg={4}><Card sx={{p:2,maxHeight:650,overflow:'auto'}}><Typography variant="h6" fontWeight={800}>Collaboration timeline</Typography><Typography variant="body2" color="text.secondary" sx={{mb:2}}>Every item comes from the event stream.</Typography>{(activity.events??[]).slice(-30).reverse().map(event=><Box className="timeline-item" key={event.event_id}><span className={`event-dot ${event.event_type.includes('failed')?'bad':event.event_type.includes('succeeded')?'good':''}`}/><Box><Typography variant="body2" fontWeight={700}>{eventText(event)}</Typography><Typography variant="caption" color="text.secondary">{new Date(event.occurred_at).toLocaleTimeString()}</Typography></Box></Box>)}</Card></Grid>
      </Grid>
      {reportReady.includes(activity.run.status)&&<Button size="large" variant="contained" onClick={()=>onReport(activity.run.id)}>Open final report and agent impact</Button>}
    </>}
  </Stack>;
}

function eventText(event:RunEvent){
  const name=(event.node_id??'workflow').replaceAll('_',' ');
  if(event.event_type==='node.started')return `${name} started working`;
  if(event.event_type==='node.succeeded')return `${name} shared its result`;
  if(event.event_type==='node.degraded')return `${name} used a degraded path`;
  if(event.event_type==='node.failed')return `${name} failed`;
  if(event.event_type==='run.started')return 'Workflow accepted the analysis request';
  if(event.event_type==='run.pause_requested')return 'User requested a safe pause';
  if(event.event_type==='run.paused')return 'Workflow saved a checkpoint and paused';
  if(event.event_type==='run.resume_requested')return 'User resumed the workflow from its checkpoint';
  if(event.event_type==='run.completed')return 'Portfolio manager completed the report';
  return `${name}: ${event.event_type.replaceAll('.',' ')}`;
}

function impact(output:unknown,state:string){
  if(state==='waiting'||state==='ready')return 'Waiting for required evidence.';
  if(state==='started')return 'Working with its typed inputs now...';
  if(!output)return state==='succeeded'?'Result sent to the next workflow stage.':'No output available.';
  if(typeof output==='object'){
    const data=output as Record<string,unknown>;
    if(data.summary)return String(data.summary);
    if(data.position)return `${String(data.position).toUpperCase()} case sent to the research debate.`;
    if(data.profile)return `${String(data.profile)} risk view joined the final risk review.`;
    if(data.action)return `${String(data.action)} proposal with ${Math.round(Number(data.confidence??0)*100)}% confidence.`;
  }
  return 'Result changed the inputs of the next connected nodes.';
}
