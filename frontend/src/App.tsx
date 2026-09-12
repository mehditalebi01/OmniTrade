import {useEffect,useState} from 'react';
import {AppBar,Box,Button,Chip,Container,Tab,Tabs,Toolbar,Typography} from '@mui/material';
import HubIcon from '@mui/icons-material/Hub';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import AnalysisPage from './components/AnalysisPage';
import AgentRoom from './components/AgentRoom';
import RunsPage from './components/RunsPage';
import ReportsPage from './components/ReportsPage';
import WorkflowStudio from './components/WorkflowStudio';
import ProfilePage from './components/ProfilePage';
import ConnectionsPage from './components/ConnectionsPage';
import UserGuidePage from './components/UserGuidePage';
import {AUTH_EXPIRED_EVENT,hasToken,logout} from './api';

const labels=['Overview','New Analysis','Agent Room','Run History','Reports','Workflow Lab','Profile','Connections','How to Use'];

export default function App(){
  const[authenticated,setAuthenticated]=useState(hasToken());
  const[tab,setTab]=useState(0);
  const[focusRun,setFocusRun]=useState<string>();
  useEffect(()=>{
    const sessionExpired=()=>setAuthenticated(false);
    window.addEventListener(AUTH_EXPIRED_EVENT,sessionExpired);
    return()=>window.removeEventListener(AUTH_EXPIRED_EVENT,sessionExpired);
  },[]);
  if(!authenticated)return <Login onLogin={()=>setAuthenticated(true)}/>;
  function showLive(id?:string){setFocusRun(id);setTab(2);}
  function showReport(id?:string){setFocusRun(id);setTab(4);}
  return <Box sx={{minHeight:'100vh'}}>
    <AppBar position="sticky" elevation={0} className="topbar">
      <Toolbar><HubIcon color="secondary" sx={{mr:1.5}}/><Box sx={{flexGrow:1}}><Typography variant="h6" sx={{fontWeight:900,lineHeight:1.1}}>OmniTrade AI</Typography><Typography variant="caption" color="text.secondary">Multi-Agent Financial Intelligence</Typography></Box><Chip label="No trade execution" color="warning" variant="outlined" sx={{mr:2,display:{xs:'none',sm:'flex'}}}/><Button color="inherit" onClick={()=>{logout();setAuthenticated(false);}}>Sign out</Button></Toolbar>
      <Tabs value={tab} onChange={(_,value)=>setTab(value)} variant="scrollable" scrollButtons="auto" sx={{px:{xs:1,md:3}}}>{labels.map(label=><Tab key={label} label={label}/>)}</Tabs>
    </AppBar>
    <Container maxWidth="xl" sx={{py:3}}>
      {tab===0&&<Dashboard onNew={()=>setTab(1)} onLive={showLive} onReports={()=>setTab(4)}/>}
      {tab===1&&<AnalysisPage onCreated={id=>showLive(id)}/>}
      {tab===2&&<AgentRoom focusId={focusRun} onReport={id=>showReport(id)}/>}
      {tab===3&&<RunsPage focusId={focusRun} onOpenReport={showReport}/>}
      {tab===4&&<ReportsPage focusId={focusRun}/>}
      {tab===5&&<WorkflowStudio/>}
      {tab===6&&<ProfilePage/>}
      {tab===7&&<ConnectionsPage/>}
      {tab===8&&<UserGuidePage/>}
    </Container>
  </Box>;
}
