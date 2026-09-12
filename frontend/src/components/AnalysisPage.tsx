import { useEffect, useState } from 'react';
import {
  Alert, Autocomplete, Box, Button, Card, CardContent, Checkbox, Chip,
  FormControlLabel, Grid, MenuItem, Slider, Stack, Switch, TextField, Typography,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { createRun, getAnalysisOptions, getProfile, listWorkflows } from '../api';
import type { AnalysisOptions, Budget, RunConfiguration } from '../types';
import { activeWorkflow } from '../workflows';

const defaultConfig: RunConfiguration = {
  data_mode: 'live', analysts: ['market', 'fundamentals', 'news', 'sentiment'],
  research_depth: 2, risk_profile: 'balanced', report_detail: 'standard',
  output_language: 'English', base_currency: 'USD', allow_degraded: true,
  evidence_freshness_hours: 72, quick_model: 'deterministic-fixture',
  deep_model: 'deterministic-fixture',
  model_provider: 'fixture', market_providers: ['yfinance'], fundamental_providers: ['yfinance'],
  news_providers: ['yfinance'], sentiment_providers: ['yfinance'], macro_providers: ['fred'], temperature: null,
  model_max_retries: 2, reasoning_effort: 'medium',
};
const defaultBudget: Budget = {
  max_runtime_seconds: 900, max_model_calls: 30, max_provider_calls: 30,
  max_tokens: 40000, max_parallel_nodes: 8,
};
const emptyOptions: AnalysisOptions = {
  tickers: [], quick_models: [], deep_models: [], languages: [], currencies: [], data_modes: [], model_providers: [], provider_models: {}, data_providers: [], data_provider_labels: {}, data_provider_capabilities: {},
};

export function optionControlMode(values: string[]): 'empty' | 'fixed' | 'select' {
  if (!values.length) return 'empty';
  return values.length === 1 ? 'fixed' : 'select';
}

export function providerRoles(options: AnalysisOptions) {
  return options.data_providers.map(name => ({
    name,
    label: options.data_provider_labels[name] ?? name.replaceAll('_', ' '),
    capabilities: options.data_provider_capabilities[name] ?? [],
  }));
}

function FixedOption({ label, value }: { label: string; value: string }) {
  return <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, p: 1.4, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Chip label={value.replaceAll('_', ' ')} color="primary" variant="outlined"/>
  </Box>;
}

export default function AnalysisPage({ onCreated }: { onCreated: (id: string) => void }) {
  const [options, setOptions] = useState(emptyOptions);
  const [version, setVersion] = useState('');
  const [workflowLabel, setWorkflowLabel] = useState('');
  const [ticker, setTicker] = useState('AAPL');
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [config, setConfig] = useState(defaultConfig);
  const [budget, setBudget] = useState(defaultBudget);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    void Promise.all([listWorkflows(), getProfile(), getAnalysisOptions()])
      .then(([items, profile, available]) => {
        const workflow = activeWorkflow(items);
        setVersion(workflow?.published_version_id ?? '');
        setWorkflowLabel(workflow?.published_version_id ? `${workflow.definition.name} · version ${workflow.version}` : '');
        setOptions(available);
        setTicker(available.tickers.includes(profile.default_ticker) ? profile.default_ticker : available.tickers[0] ?? 'AAPL');
        const modelProvider = available.model_providers.includes(profile.default_configuration.model_provider) ? profile.default_configuration.model_provider : available.model_providers[0] ?? 'fixture';
        const models = available.provider_models[modelProvider] ?? available.quick_models;
        const chain = (preferred: string[], capability: string) => {
          const candidates = available.data_providers.filter(name => available.data_provider_capabilities[name]?.includes(capability));
          const selected = preferred.filter(name => candidates.includes(name));
          return selected.length ? selected : candidates.slice(0, 1);
        };
        setConfig({
          ...profile.default_configuration,
          data_mode: available.data_modes.includes(profile.default_configuration.data_mode) ? profile.default_configuration.data_mode : available.data_modes[0] ?? 'live',
          model_provider: modelProvider,
          quick_model: models.includes(profile.default_configuration.quick_model) ? profile.default_configuration.quick_model : models[0] ?? '',
          deep_model: models.includes(profile.default_configuration.deep_model) ? profile.default_configuration.deep_model : models.at(-1) ?? '',
          market_providers: chain(profile.default_configuration.market_providers, 'market'),
          fundamental_providers: chain(profile.default_configuration.fundamental_providers, 'fundamentals'),
          news_providers: chain(profile.default_configuration.news_providers, 'news'),
          sentiment_providers: chain(profile.default_configuration.sentiment_providers, 'sentiment'),
          macro_providers: chain(profile.default_configuration.macro_providers, 'macro'),
        });
      })
      .catch(error => setMessage(error instanceof Error ? error.message : String(error)));
  }, []);

  const update = <K extends keyof RunConfiguration>(key: K, value: RunConfiguration[K]) =>
    setConfig(current => ({ ...current, [key]: value }));
  const toggleAnalyst = (name: string) => update(
    'analysts',
    config.analysts.includes(name)
      ? config.analysts.filter(value => value !== name)
      : [...config.analysts, name],
  );
  const chainFields = [
    ['market_providers', 'Market data chain', 'market', 'Price, volume, and technical market evidence.'],
    ['fundamental_providers', 'Fundamental data chain', 'fundamentals', 'Company accounts, valuation, and business facts.'],
    ['macro_providers', 'Macro data chain', 'macro', 'Rates, economic series, and prediction-market evidence.'],
    ['news_providers', 'News data chain', 'news', 'Current company and market articles.'],
    ['sentiment_providers', 'News and social sentiment chain', 'sentiment', 'Sentiment scores from verified text sources.'],
  ] as [keyof RunConfiguration, string, string, string][];
  const providerModels = options.provider_models[config.model_provider] ?? [];
  const verifiedProviderRoles = providerRoles(options);

  const toggleChainProvider = (key: keyof RunConfiguration, name: string) => {
    const current = config[key] as string[];
    update(key, (current.includes(name) ? current.filter(value => value !== name) : [...current, name]) as RunConfiguration[typeof key]);
  };

  async function start() {
    setBusy(true);
    setMessage('');
    try {
      const run = await createRun(
        version, ticker, `${date}T00:00:00.000Z`, config, budget,
      );
      onCreated(run.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  return <Stack spacing={2}>
    <Box>
      <Typography variant="h4" fontWeight={800}>New Analysis</Typography>
      <Typography color="text.secondary">The selected real providers, models, agents, risk rules, and report options control this workflow run.</Typography>
    </Box>
    {message && <Alert severity="error">{message}</Alert>}
    {!version && <Alert severity="warning">Open Workflow Lab, validate the graph, and publish it before starting an analysis.</Alert>}
    {(!options.model_providers.length||!options.data_providers.length)&&<Alert severity="warning">Open Connections and verify at least one AI model provider and the real data providers needed by this workflow.</Alert>}
    <Grid container spacing={2}>
      <Grid item xs={12} md={6}>
        <Card><CardContent>
          <Typography variant="h6" fontWeight={800} gutterBottom>1. Instrument and data</Typography>
          <Stack spacing={2}>
            {workflowLabel && <Alert severity="info">The latest published Workflow Lab graph is used automatically: <b>{workflowLabel}</b>.</Alert>}
            <Autocomplete
              disableClearable options={options.tickers} value={ticker}
              onChange={(_, value) => setTicker(value)}
              renderInput={params => <TextField {...params} label="Stock ticker" helperText="Only supported stock symbols are listed" />}
            />
            <TextField label="Analysis date" type="date" value={date} inputProps={{ max: new Date().toISOString().slice(0, 10) }} onChange={event => setDate(event.target.value)} InputLabelProps={{ shrink: true }} />
            {options.data_modes.length > 1 && <TextField select label="Data mode" value={config.data_mode} onChange={event => update('data_mode', event.target.value)}>
              {options.data_modes.map(mode => <MenuItem value={mode} key={mode}>{mode === 'recorded' ? 'Recorded data - tests only' : 'Real provider data'}</MenuItem>)}
            </TextField>}
            <Box sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
              <Typography variant="subtitle2" fontWeight={800} gutterBottom>Verified provider map</Typography>
              <Typography variant="caption" color="text.secondary">A provider appears only in the chains supported by its real API.</Typography>
              <Stack spacing={1} sx={{ mt: 1 }}>
                {verifiedProviderRoles.map(item => <Box key={item.name} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                  <Typography variant="body2" fontWeight={700}>{item.label}</Typography>
                  <Stack direction="row" gap={.5} flexWrap="wrap" justifyContent="flex-end">{item.capabilities.map(capability => <Chip key={capability} size="small" label={capability.replaceAll('_', ' ')} variant="outlined"/>)}</Stack>
                </Box>)}
              </Stack>
            </Box>
            <Alert severity="info">FRED and Polymarket are macro sources. Yahoo Finance covers market, company, news, and news sentiment. Alpha Vantage can add choices to all five chains after its API key is verified.</Alert>
            {chainFields.map(([key, label, capability, help]) => {
              const values = options.data_providers.filter(name => options.data_provider_capabilities[name]?.includes(capability));
              const mode = optionControlMode(values);
              if (mode === 'empty') return <Alert key={key} severity="warning">No verified {label.toLowerCase()}. Connect one in Connections.</Alert>;
              if (mode === 'fixed') return <Box key={key}><FixedOption label={label} value={options.data_provider_labels[values[0]] ?? values[0]}/><Typography variant="caption" color="text.secondary">{help}</Typography></Box>;
              return <Box key={key} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                <Typography variant="subtitle2" fontWeight={800}>{label}</Typography>
                <Typography variant="caption" color="text.secondary">{help} Select one or more sources.</Typography>
                <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 1 }}>
                  {values.map(name => <FormControlLabel key={name} sx={{ m: 0, pr: 1.2, border: '1px solid', borderColor: (config[key] as string[]).includes(name) ? 'primary.main' : 'divider', borderRadius: 2 }} control={<Checkbox size="small" checked={(config[key] as string[]).includes(name)} onChange={() => toggleChainProvider(key, name)}/>} label={options.data_provider_labels[name] ?? name.replaceAll('_', ' ')}/>) }
                </Stack>
              </Box>;
            })}
          </Stack>
        </CardContent></Card>
      </Grid>
      <Grid item xs={12} md={6}>
        <Card><CardContent>
          <Typography variant="h6" fontWeight={800}>2. Specialist branches</Typography>
          <Typography variant="body2" color="text.secondary">Selected agents are the only specialist nodes executed for this run.</Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
            {['market', 'fundamentals', 'news', 'sentiment'].map(name => <FormControlLabel key={name} control={<Checkbox checked={config.analysts.includes(name)} onChange={() => toggleAnalyst(name)} />} label={name} />)}
          </Box>
          <Typography gutterBottom>Research depth: {config.research_depth} bounded rounds</Typography>
          <Slider min={1} max={5} marks value={config.research_depth} onChange={(_, value) => update('research_depth', value as number)} />
          <TextField fullWidth select label="Risk profile" value={config.risk_profile} onChange={event => update('risk_profile', event.target.value)}>
            <MenuItem value="conservative">Conservative</MenuItem><MenuItem value="balanced">Balanced</MenuItem><MenuItem value="aggressive">Aggressive</MenuItem>
          </TextField>
          <FormControlLabel control={<Switch checked={config.allow_degraded} onChange={event => update('allow_degraded', event.target.checked)} />} label="Allow a report when optional branches fail" />
        </CardContent></Card>
      </Grid>
      <Grid item xs={12} md={6}>
        <Card><CardContent>
          <Typography variant="h6" fontWeight={800} gutterBottom>3. Models and report</Typography>
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">Your Profile default is preselected. If two or more providers are verified, you can change it for this run.</Typography>
            {optionControlMode(options.model_providers) === 'empty' ? <Alert severity="warning">No verified AI provider. Connect and verify one in Connections.</Alert> : optionControlMode(options.model_providers) === 'fixed' ? <FixedOption label="Only verified model provider" value={options.model_providers[0]}/> : <TextField select label="Model provider" value={config.model_provider} onChange={event => { const name = event.target.value; const models = options.provider_models[name] ?? []; setConfig(current => ({ ...current, model_provider: name, quick_model: models[0] ?? '', deep_model: models.at(-1) ?? '' })); }}>
              {options.model_providers.map(name => <MenuItem value={name} key={name}>{name.replaceAll('_', ' ')}</MenuItem>)}
            </TextField>}
            {optionControlMode(providerModels) === 'empty' ? <Alert severity="warning">No models are configured for this provider.</Alert> : optionControlMode(providerModels) === 'fixed' ? <FixedOption label="Quick and deep model" value={providerModels[0]}/> : <>
              <TextField select label="Quick analysis model" value={config.quick_model} onChange={event => update('quick_model', event.target.value)}>
                {providerModels.map(model => <MenuItem value={model} key={model}>{model}</MenuItem>)}
              </TextField>
              <TextField select label="Deep reasoning model" value={config.deep_model} onChange={event => update('deep_model', event.target.value)}>
                {providerModels.map(model => <MenuItem value={model} key={model}>{model}</MenuItem>)}
              </TextField>
            </>}
            <TextField select label="Reasoning effort" value={config.reasoning_effort} onChange={event=>update('reasoning_effort',event.target.value)}><MenuItem value="low">Low</MenuItem><MenuItem value="medium">Medium</MenuItem><MenuItem value="high">High</MenuItem></TextField>
            <TextField type="number" label="Temperature (empty uses provider default)" value={config.temperature??''} inputProps={{min:0,max:2,step:0.1}} onChange={event=>update('temperature',event.target.value===''?null:Number(event.target.value))}/>
            <TextField type="number" label="Model retries" value={config.model_max_retries} inputProps={{min:0,max:5,step:1}} onChange={event=>update('model_max_retries',Math.max(0,Math.min(5,Number(event.target.value))))}/>
            <TextField select label="Report detail" value={config.report_detail} onChange={event => update('report_detail', event.target.value)}>
              <MenuItem value="summary">Summary</MenuItem><MenuItem value="standard">Standard</MenuItem><MenuItem value="detailed">Detailed</MenuItem>
            </TextField>
            <TextField select label="Output language" value={config.output_language} onChange={event => update('output_language', event.target.value)}>
              {options.languages.map(language => <MenuItem value={language} key={language}>{language}</MenuItem>)}
            </TextField>
            <TextField select label="Base currency" value={config.base_currency} onChange={event => update('base_currency', event.target.value)}>
              {options.currencies.map(currency => <MenuItem value={currency} key={currency}>{currency}</MenuItem>)}
            </TextField>
            <TextField type="number" label="Evidence freshness (hours)" value={config.evidence_freshness_hours} inputProps={{min:1,max:720,step:1}} onChange={event => update('evidence_freshness_hours', Math.max(1,Math.min(720,Number(event.target.value))))} />
          </Stack>
        </CardContent></Card>
      </Grid>
      <Grid item xs={12} md={6}>
        <Card><CardContent>
          <Typography variant="h6" fontWeight={800} gutterBottom>4. Safety budgets</Typography>
          <Grid container spacing={1.5}>
            {([['max_runtime_seconds', 'Runtime seconds', 10, 1800], ['max_model_calls', 'Model calls', 0, 100], ['max_provider_calls', 'Provider calls', 0, 200], ['max_tokens', 'Token budget', 0, 1000000], ['max_parallel_nodes', 'Parallel nodes', 1, 32]] as [keyof Budget, string, number, number][]).map(([key, label, min, max]) => <Grid item xs={6} key={key}><TextField fullWidth type="number" label={label} value={budget[key]} inputProps={{min,max,step:1}} onChange={event => setBudget(current => ({ ...current, [key]: Math.max(min,Math.min(max,Number(event.target.value))) }))} /></Grid>)}
          </Grid>
        </CardContent></Card>
      </Grid>
    </Grid>
    <Button size="large" variant="contained" startIcon={<PlayArrowIcon />} disabled={busy || !version || !ticker || !config.analysts.length || !config.model_provider || !config.quick_model || !config.deep_model || !config.market_providers.length || !config.fundamental_providers.length || !config.news_providers.length || !config.sentiment_providers.length || !config.macro_providers.length} onClick={start}>Start customized real analysis</Button>
  </Stack>;
}
