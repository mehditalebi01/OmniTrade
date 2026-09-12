import{useEffect,useState}from'react';
import{Alert,Autocomplete,Box,Button,Card,CardContent,Chip,Divider,MenuItem,Stack,TextField,Typography}from'@mui/material';
import SaveIcon from'@mui/icons-material/Save';
import{getAnalysisOptions,getProfile,saveProfile}from'../api';
import type{AnalysisOptions,UserProfile}from'../types';

const emptyOptions:AnalysisOptions={tickers:[],quick_models:[],deep_models:[],languages:[],currencies:[],data_modes:[],model_providers:[],provider_models:{},data_providers:[],data_provider_labels:{},data_provider_capabilities:{}};
function FixedDefault({label,value}:{label:string;value:string}){return<Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:2,p:1.4,border:'1px solid',borderColor:'divider',borderRadius:2}}><Typography variant="body2" color="text.secondary">{label}</Typography><Chip label={value.replaceAll('_',' ')} color="primary" variant="outlined"/></Box>}

export default function ProfilePage(){
  const[profile,setProfile]=useState<UserProfile>();
  const[options,setOptions]=useState<AnalysisOptions>(emptyOptions);
  const[message,setMessage]=useState('');
  useEffect(()=>{void Promise.all([getProfile(),getAnalysisOptions()]).then(([value,available])=>{const provider=available.model_providers.includes(value.default_configuration.model_provider)?value.default_configuration.model_provider:available.model_providers[0]??'';const models=available.provider_models[provider]??[];setOptions(available);setProfile({...value,default_configuration:{...value.default_configuration,data_mode:'live',model_provider:provider,quick_model:models.includes(value.default_configuration.quick_model)?value.default_configuration.quick_model:models[0]??'',deep_model:models.includes(value.default_configuration.deep_model)?value.default_configuration.deep_model:models.at(-1)??''}})}).catch(error=>setMessage(String(error)))},[]);
  if(!profile)return<Alert severity="info">Loading profile...</Alert>;
  const config=profile.default_configuration;
  const policy=profile.investor_policy;
  const models=options.provider_models[config.model_provider]??[];
  const updatePolicy=(key:keyof typeof policy,value:string|number|string[])=>setProfile({...profile,investor_policy:{...policy,[key]:value}});
  const updateConfig=(values:Partial<typeof config>)=>setProfile({...profile,default_configuration:{...config,...values}});
  return<Stack spacing={2} sx={{maxWidth:850}}>
    <Typography variant="h4" fontWeight={800}>Profile and Investment Policy</Typography>
    <Typography color="text.secondary">Defaults fill the analysis form. Investment limits are copied into each run and change its risk validation.</Typography>
    {message&&<Alert severity={message==='Profile saved'?'success':'error'}>{message}</Alert>}
    <Card><CardContent><Stack spacing={2}>
      <Typography variant="h6">Identity and defaults</Typography>
      <TextField label="Display name" value={profile.display_name} onChange={event=>setProfile({...profile,display_name:event.target.value})}/>
      <TextField label="Email (not used for decisions)" value={profile.email} onChange={event=>setProfile({...profile,email:event.target.value})}/>
      <Autocomplete disableClearable options={options.tickers} value={profile.default_ticker} onChange={(_,value)=>setProfile({...profile,default_ticker:value})} renderInput={params=><TextField {...params} label="Default stock ticker" helperText="Choose a supported stock symbol"/>}/>
      <Alert severity="success">All normal analyses use verified real provider data. There is no fake-data mode to select.</Alert>
      <Typography variant="subtitle1" fontWeight={800}>Default AI models</Typography>
      {!options.model_providers.length?<Alert severity="warning">Verify an AI provider in Connections before choosing model defaults.</Alert>:options.model_providers.length===1?<FixedDefault label="Only verified provider" value={options.model_providers[0]}/>:<TextField select label="Default model provider" value={config.model_provider} helperText="This becomes the first choice on New Analysis." onChange={event=>{const provider=event.target.value;const choices=options.provider_models[provider]??[];updateConfig({model_provider:provider,quick_model:choices[0]??'',deep_model:choices.at(-1)??''})}}>{options.model_providers.map(provider=><MenuItem key={provider} value={provider}>{provider.replaceAll('_',' ')}</MenuItem>)}</TextField>}
      {models.length===1?<FixedDefault label="Quick and deep model" value={models[0]}/>:models.length>1?<><TextField select label="Default quick analysis model" value={config.quick_model} onChange={event=>updateConfig({quick_model:event.target.value})}>{models.map(model=><MenuItem key={model} value={model}>{model}</MenuItem>)}</TextField><TextField select label="Default deep reasoning model" value={config.deep_model} onChange={event=>updateConfig({deep_model:event.target.value})}>{models.map(model=><MenuItem key={model} value={model}>{model}</MenuItem>)}</TextField></>:null}
      <TextField select label="Default risk profile" value={config.risk_profile} onChange={event=>updateConfig({risk_profile:event.target.value})}><MenuItem value="conservative">Conservative</MenuItem><MenuItem value="balanced">Balanced</MenuItem><MenuItem value="aggressive">Aggressive</MenuItem></TextField>
      <TextField type="number" label="Default research depth" value={config.research_depth} onChange={event=>updateConfig({research_depth:Number(event.target.value)})}/>
      <TextField select label="Default report detail" value={config.report_detail} onChange={event=>updateConfig({report_detail:event.target.value})}><MenuItem value="summary">Summary</MenuItem><MenuItem value="standard">Standard</MenuItem><MenuItem value="detailed">Detailed</MenuItem></TextField>
      <Divider/>
      <Typography variant="h6">Investment policy used by the risk agents</Typography>
      <TextField select label="Investment horizon" value={policy.investment_horizon} onChange={event=>updatePolicy('investment_horizon',event.target.value)}><MenuItem value="short">Short term</MenuItem><MenuItem value="medium">Medium term</MenuItem><MenuItem value="long">Long term</MenuItem></TextField>
      <TextField select label="Experience level" value={policy.experience_level} onChange={event=>updatePolicy('experience_level',event.target.value)}><MenuItem value="beginner">Beginner</MenuItem><MenuItem value="intermediate">Intermediate</MenuItem><MenuItem value="advanced">Advanced</MenuItem></TextField>
      <TextField type="number" label="Maximum acceptable loss (%)" inputProps={{min:1,max:50}} value={policy.maximum_loss_percent} onChange={event=>updatePolicy('maximum_loss_percent',Number(event.target.value))}/>
      <TextField type="number" label="Maximum position size (%)" inputProps={{min:1,max:100}} value={policy.maximum_position_percent} onChange={event=>updatePolicy('maximum_position_percent',Number(event.target.value))}/>
      <TextField label="Excluded sectors (comma separated)" value={policy.excluded_sectors.join(', ')} onChange={event=>updatePolicy('excluded_sectors',event.target.value.split(',').map(value=>value.trim()).filter(Boolean))}/>
      <Alert severity="info">Only investment preferences affect decisions. Your name and email never change a recommendation.</Alert>
      <Button variant="contained" startIcon={<SaveIcon/>} onClick={async()=>{try{setProfile(await saveProfile(profile));setMessage('Profile saved')}catch(error){setMessage(String(error))}}}>Save profile</Button>
    </Stack></CardContent></Card>
  </Stack>;
}
