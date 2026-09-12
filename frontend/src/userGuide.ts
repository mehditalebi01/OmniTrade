export interface GuideTopic {
  range: string;
  title: string;
  summary: string;
  steps: string[];
}

export const guideTopics: GuideTopic[] = [
  { range: '0–10', title: 'Start the website', summary: 'Start all services and sign in.', steps: [
    'Open a terminal in the OmniTradeAI project folder.',
    'Run docker compose up --build -d.',
    'Open http://localhost:5173 and sign in with your local account.',
    'If the token expired, sign in again. Do not reuse an old browser token.',
  ] },
  { range: '10–25', title: 'Connect AI', summary: 'Connect and verify the models used by agents.', steps: [
    'Open Connections and select an AI provider.',
    'Enter its credential. For Bedrock, also select the AWS region and model IDs.',
    'Select Save session connection, then Verify now.',
    'Only verified providers and models appear in Profile and New Analysis.',
  ] },
  { range: '25–35', title: 'Connect data', summary: 'Connect real sources and understand their roles.', steps: [
    'Select Connect supported keyless sources for Yahoo Finance and Polymarket.',
    'For FRED or Alpha Vantage, select the provider and enter its API key.',
    'Save and verify the connection. Failed providers are not used.',
    'FRED and Polymarket appear in Macro. Yahoo Finance appears in Market, Fundamentals, News, and Sentiment.',
    'Reddit and StockTwits are optional. Their public endpoints may return HTTP 403 or 429.',
  ] },
  { range: '35–45', title: 'Set your profile', summary: 'Save useful defaults and risk limits.', steps: [
    'Open Profile and choose the default stock and AI models.',
    'Set investment horizon, experience level, loss limit, and position limit.',
    'Add excluded sectors when needed.',
    'Save the profile. These values affect risk checks and future analysis defaults.',
  ] },
  { range: '45–65', title: 'Create an analysis', summary: 'Choose the stock, agents, providers, and report settings.', steps: [
    'Open New Analysis. The latest published Workflow Lab graph is used automatically.',
    'Choose the stock and analysis date.',
    'Review the verified provider map and select one or more sources in chains that have alternatives.',
    'Choose specialist agents, research depth, risk profile, AI models, and report detail.',
    'Choose output language, currency, and evidence freshness.',
  ] },
  { range: '65–75', title: 'Check safety limits', summary: 'Set clear limits before the run starts.', steps: [
    'Review maximum runtime, model calls, provider calls, tokens, and parallel nodes.',
    'Keep degraded mode enabled only when an optional branch may fail safely.',
    'Select Start customized real analysis.',
  ] },
  { range: '75–85', title: 'Watch agents work', summary: 'Follow the real sequence and each agent output.', steps: [
    'Open Agent Room after starting the run.',
    'Follow evidence collection, normalization, specialist agents, debate, risk views, and manager decision.',
    'Check retries, degraded branches, or failures when a node does not finish.',
    'Open Run History to pause an active run after its current node batch.',
    'Use Resume from checkpoint for a paused, failed, or interrupted run. Reconnect old live providers first.',
  ] },
  { range: '85–95', title: 'Read the report', summary: 'Review the decision, evidence, and all agent views.', steps: [
    'Open Reports and select a date or saved run.',
    'Read each analyst view, bull and bear cases, three risk views, and the final manager decision.',
    'Check warnings, evidence sources, workflow version, and lineage.',
    'Export the report as PDF or JSON when needed.',
  ] },
  { range: '95–100', title: 'Customize the workflow', summary: 'Edit the graph only when advanced control is needed.', steps: [
    'Open Workflow Lab and edit nodes or compatible edges.',
    'Use Undo if needed, then Save and Validate.',
    'Fix every validation error before Publish becomes available.',
    'Publish the graph. The next New Analysis run uses this new version automatically.',
  ] },
];
