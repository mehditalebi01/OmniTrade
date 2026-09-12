import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert, Box, Button, Card, Chip, CircularProgress, Divider, LinearProgress,
  Stack, Typography,
} from '@mui/material';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import DownloadIcon from '@mui/icons-material/Download';
import { downloadReport, getReport, listReports } from '../api';
import type { AgentAnalysis, DebateCase, ReportData, ReportSummary, RiskAnalysis } from '../types';

const dateKey = (value: string) => {
  const date = new Date(value);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

export default function ReportsPage({ focusId }: { focusId?: string }) {
  const [items, setItems] = useState<ReportSummary[]>([]);
  const [report, setReport] = useState<ReportData>();
  const [selectedReportId, setSelectedReportId] = useState<string>();
  const [selectedDate, setSelectedDate] = useState('');
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');

  const open = useCallback(async (id: string) => {
    setBusy(true);
    try {
      setSelectedReportId(id);
      setReport(normalizeReport(await getReport(id)));
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void listReports().then((result) => {
      setItems(result);
      const selected = result.find((item) => item.run_id === focusId) ?? result[0];
      if (selected) {
        const when = new Date(selected.created_at);
        setSelectedDate(dateKey(selected.created_at));
        setMonth(new Date(when.getFullYear(), when.getMonth(), 1));
        void open(selected.run_id);
      }
    }).catch((reason) => setError(String(reason))).finally(() => setBusy(false));
  }, [focusId, open]);

  const byDate = useMemo(() => items.reduce<Record<string, ReportSummary[]>>((map, item) => {
    (map[dateKey(item.created_at)] ??= []).push(item);
    return map;
  }, {}), [items]);
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const total = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const cells = [...Array(first.getDay()).fill(null), ...Array.from({ length: total }, (_, index) => index + 1)];
  const dayItems = byDate[selectedDate] ?? [];

  return <Stack spacing={2}>
    <Box>
      <Typography variant="h4" fontWeight={800}>Reports</Typography>
      <Typography color="text.secondary">Browse saved reports and read every agent point of view.</Typography>
    </Box>
    {error && <Alert severity="error">{error}</Alert>}
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '390px 1fr' }, gap: 2 }}>
      <Stack spacing={2}>
        <Card sx={{ p: 2 }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Button aria-label="Previous month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}><NavigateBeforeIcon /></Button>
            <Typography fontWeight={800}>{month.toLocaleString(undefined, { month: 'long', year: 'numeric' })}</Typography>
            <Button aria-label="Next month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}><NavigateNextIcon /></Button>
          </Stack>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: .5, mt: 1 }}>
            {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, index) => <Typography key={`${day}${index}`} align="center" variant="caption" color="text.secondary">{day}</Typography>)}
            {cells.map((day, index) => {
              if (!day) return <Box key={`empty${index}`} />;
              const key = `${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
              const count = byDate[key]?.length ?? 0;
              return <Button key={key} onClick={() => setSelectedDate(key)} variant={selectedDate === key ? 'contained' : 'text'} sx={{ minWidth: 0, aspectRatio: '1', position: 'relative' }}>
                {day}{count > 0 && <Box sx={{ position: 'absolute', bottom: 3, width: 5, height: 5, borderRadius: '50%', background: '#35cc61' }} />}
              </Button>;
            })}
          </Box>
        </Card>
        <Card sx={{ p: 2 }}>
          <Typography fontWeight={800}>{selectedDate || 'Select a date'}</Typography>
          {dayItems.length ? dayItems.map((item) => <Box key={item.run_id} sx={{ py: 1.5, cursor: 'pointer' }} onClick={() => void open(item.run_id)}>
            <Stack direction="row" justifyContent="space-between"><Typography fontWeight={800}>{item.ticker}</Typography><Chip size="small" label={`${item.action} · ${Math.round(item.confidence * 100)}%`} /></Stack>
            <Typography variant="caption">{new Date(item.created_at).toLocaleTimeString()}</Typography>
          </Box>) : <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>No reports on this date.</Typography>}
        </Card>
      </Stack>
      <Card sx={{ p: { xs: 2, md: 4 }, minHeight: 600 }}>
        {busy ? <CircularProgress /> : report ? <ReportView report={report} reportId={selectedReportId} /> : <Alert severity="info">Choose a report from the calendar.</Alert>}
      </Card>
    </Box>
  </Stack>;
}

function AnalystCard({ analysis }: { analysis: AgentAnalysis }) {
  return <Card variant="outlined" sx={{ p: 2 }}>
    <Stack direction="row" justifyContent="space-between" gap={1}>
      <Typography variant="h6" fontWeight={800}>{analysis.agent}</Typography>
      <Chip size="small" label={`${analysis.viewpoint} · ${Math.round(analysis.confidence * 100)}%`} />
    </Stack>
    <Typography sx={{ mt: 1 }}>{analysis.summary}</Typography>
    {analysis.key_points.length > 0 && <Box sx={{ mt: 1 }}><Typography variant="subtitle2">Main observations</Typography>{analysis.key_points.map((point) => <Typography key={point} variant="body2">• {point}</Typography>)}</Box>}
    {analysis.risks.length > 0 && <Alert severity="warning" sx={{ mt: 1 }}>{analysis.risks.join(' · ')}</Alert>}
    {analysis.evidence_refs.length > 0 && <Typography variant="caption" color="text.secondary">Evidence: {analysis.evidence_refs.join(', ')}</Typography>}
  </Card>;
}

export function debateSupport(debate?: DebateCase): number {
  return debate?.support ?? debate?.confidence ?? 0;
}

function DebateCard({ title, debate, color }: { title: string; debate?: DebateCase; color: 'success' | 'error' }) {
  const support = debateSupport(debate);
  return <Card variant="outlined" sx={{ p: 2, borderColor: `${color}.main` }}>
    <Typography variant="h6" color={`${color}.main`} fontWeight={900}>{title}</Typography>
    {debate ? <><Typography fontWeight={700}>{debate.agent}</Typography><Stack direction="row" spacing={1} sx={{ my: 1 }}><Chip size="small" label={`Support: ${Math.round(support * 100)}%`} /><Chip size="small" label={`Evidence confidence: ${Math.round(debate.confidence * 100)}%`} /></Stack><Typography sx={{ my: 1 }}>{debate.summary}</Typography>{debate.key_points.map((point) => <Typography key={point} variant="body2">• {point}</Typography>)}{debate.counterpoints.length > 0 && <Typography variant="caption" color="text.secondary">Challenges: {debate.counterpoints.join(' · ')}</Typography>}</> : <Typography color="text.secondary">Not used in this run.</Typography>}
  </Card>;
}

function RiskCard({ view }: { view: RiskAnalysis }) {
  return <Card variant="outlined" sx={{ p: 2 }}><Stack direction="row" justifyContent="space-between"><Typography fontWeight={800}>{view.agent}</Typography><Chip size="small" label={view.stance} /></Stack><Typography sx={{ my: 1 }}>{view.summary}</Typography><Typography variant="body2"><b>Portfolio impact:</b> {view.impact}</Typography>{view.key_points.map((point) => <Typography key={point} variant="body2">• {point}</Typography>)}</Card>;
}

function ReportView({ report, reportId }: { report: ReportData; reportId?: string }) {
  const color = report.decision.action === 'BUY' ? 'success' : report.decision.action === 'SELL' ? 'error' : 'warning';
  const debate = report.research_debate ?? {};
  return <Stack spacing={3}>
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={2}><Box><Typography variant="h4" fontWeight={900}>{report.title}</Typography><Typography color="text.secondary">As of {new Date(report.as_of).toLocaleString()}</Typography></Box><Chip color={color} label={`${report.decision.action} · ${Math.round(report.decision.confidence * 100)}% confidence`} sx={{ fontSize: 16, fontWeight: 800, p: 2 }} /></Stack>
    <Alert severity="info">{report.executive_summary}</Alert>
    <Box><Typography variant="h6" fontWeight={800}>Final manager decision</Typography><Typography>{report.decision.rationale}</Typography><LinearProgress variant="determinate" value={report.decision.confidence * 100} sx={{ mt: 2, height: 9, borderRadius: 5 }} /></Box>
    <Stack direction="row" spacing={1} flexWrap="wrap">{report.decision.key_factors.map((factor) => <Chip key={factor} label={factor} />)}</Stack>
    {report.decision.warnings.map((warning) => <Alert key={warning} severity="warning">{warning}</Alert>)}

    <Divider /><Typography variant="h5" fontWeight={900}>Specialist analyst views</Typography>
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2,1fr)' }, gap: 2 }}>{(report.agent_analyses ?? []).map((analysis) => <AnalystCard key={analysis.node_id} analysis={analysis} />)}</Box>
    {(report.agent_analyses ?? []).length === 0 && <Alert severity="info">This older report has no saved specialist outputs.</Alert>}

    <Divider /><Typography variant="h5" fontWeight={900}>Bull and bear research debate</Typography>
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2,1fr)' }, gap: 2 }}><DebateCard title="Bull case" debate={debate.bull_case} color="success" /><DebateCard title="Bear case" debate={debate.bear_case} color="error" /></Box>
    {debate.manager_conclusion && <Alert severity="info"><b>Research manager:</b> {debate.manager_conclusion}</Alert>}

    {report.trading_proposal && <><Divider /><Typography variant="h5" fontWeight={900}>Trading proposal</Typography><Card variant="outlined" sx={{ p: 2 }}><Stack direction="row" justifyContent="space-between"><Typography>{report.trading_proposal.summary}</Typography><Chip label={`${report.trading_proposal.action ?? 'HOLD'} · ${Math.round((report.trading_proposal.confidence ?? 0) * 100)}%`} /></Stack>{(report.trading_proposal.conditions ?? []).map((condition) => <Typography key={condition} variant="body2">• {condition}</Typography>)}</Card></>}

    <Divider /><Typography variant="h5" fontWeight={900}>Risk team views</Typography>
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: 'repeat(3,1fr)' }, gap: 2 }}>{(report.risk_analyses ?? []).map((view) => <RiskCard key={view.agent} view={view} />)}</Box>

    <Divider /><Typography variant="h5" fontWeight={900}>Evidence and traceability</Typography>
    {(report.evidence_overview ?? []).map((item) => <Card key={item.source} variant="outlined" sx={{ p: 1.5, mb: 1 }}><Stack direction="row" justifyContent="space-between"><Typography fontWeight={800}>{item.source}</Typography><Chip size="small" label={item.status} /></Stack><Typography variant="body2">{item.summary}</Typography><Typography variant="caption" color="text.secondary">Hashes: {item.content_hashes.join(', ') || 'none'}</Typography></Card>)}
    {report.workflow_summary?.trace_id && <Typography variant="caption" color="text.secondary">Trace {report.workflow_summary.trace_id} · Workflow version {report.workflow_summary.workflow_version_id}</Typography>}

    <Divider /><Typography variant="h6" fontWeight={800}>Run settings</Typography>
    <Typography variant="body2">Analysts: {report.analysis_settings.analysts.join(', ')} · Risk: {report.analysis_settings.risk_profile} · Depth: {report.analysis_settings.research_depth} · Data: {report.analysis_settings.data_mode}</Typography>
    <Alert severity="info">{report.disclaimer}</Alert>
    {reportId && <Stack direction="row" spacing={1}><Button startIcon={<DownloadIcon />} onClick={() => void downloadReport(reportId, 'pdf')}>PDF</Button><Button startIcon={<DownloadIcon />} onClick={() => void downloadReport(reportId, 'json')}>JSON</Button></Stack>}
  </Stack>;
}

function normalizeReport(raw: ReportData): ReportData {
  if (raw.sections && raw.analysis_settings && raw.decision?.rationale) return raw;
  const decision = (raw.decision ?? {}) as ReportData['decision'];
  return {
    title: raw.title ?? 'OmniTrade report', ticker: raw.ticker ?? 'Stock', as_of: raw.as_of ?? new Date().toISOString(), generated_at: raw.generated_at ?? new Date().toISOString(), executive_summary: raw.executive_summary ?? 'This report uses an older saved format.',
    decision: { action: decision.action ?? 'NO_DECISION', confidence: decision.confidence ?? 0, rationale: decision.rationale ?? 'No structured rationale is available.', key_factors: decision.key_factors ?? [], warnings: decision.warnings ?? [] },
    sections: raw.sections ?? [], agent_analyses: [], risk_analyses: [], evidence_overview: [],
    analysis_settings: raw.analysis_settings ?? { data_mode: 'live', analysts: ['market', 'fundamentals', 'news', 'sentiment'], research_depth: 2, risk_profile: 'balanced', report_detail: 'standard', output_language: 'English', base_currency: 'USD', allow_degraded: true, evidence_freshness_hours: 72, quick_model: 'legacy', deep_model: 'legacy' },
    lineage_complete: Boolean(raw.lineage_complete), disclaimer: raw.disclaimer ?? 'Financial decision support only. OmniTrade does not execute trades.',
  };
}
