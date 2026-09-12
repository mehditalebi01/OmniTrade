# OmniTrade AI user guide

OmniTrade AI provides financial decision support. It does not execute trades,
and its result is not a guarantee.

## 0–10: Start the website

1. Open a terminal in the `OmniTradeAI` project folder.
2. Run `docker compose up --build -d`.
3. Open `http://localhost:5173`.
4. Sign in with your local account.
5. If the token expired, sign in again instead of reusing an old browser token.

## 10–25: Connect an AI provider

1. Open **Connections**.
2. Select an AI provider.
3. Enter its private credential.
4. For Amazon Bedrock, select the AWS region and enter the allowed model IDs.
5. Select **Save session connection**.
6. Select a verification model and choose **Verify now**.

Only verified providers and models appear in Profile and New Analysis. Secrets
stay in API memory for the server session. They are not returned by the API or
stored in reports.

## 25–35: Connect real data

1. Select **Connect supported keyless sources** to connect Yahoo Finance and
   Polymarket.
2. To use FRED, select **Data · FRED**, enter its API key, save, and verify.
3. To use Alpha Vantage, select **Data · Alpha Vantage**, enter its API key,
   save, and verify.
4. Check the green **Verified** status.
5. Open New Analysis and review the **Verified provider map**.

Provider roles are based on real API capabilities:

- Yahoo Finance: market, fundamentals, news, and news sentiment.
- FRED: macroeconomic series.
- Polymarket: macro and prediction-market evidence.
- Alpha Vantage: market, fundamentals, news, sentiment, and macro.
- StockTwits and Reddit: optional public sentiment feeds.

StockTwits may return HTTP 403 when it blocks public access. Reddit may return
HTTP 429 when its public rate limit is reached. These feeds are removed after a
failed verification and are never used as fake fallbacks.

## 35–45: Set your profile

1. Open **Profile**.
2. Choose the default stock, AI provider, quick model, and deep model.
3. Set the investment horizon and experience level.
4. Set the maximum acceptable loss and maximum position size.
5. Add excluded sectors when needed.
6. Select **Save profile**.

These settings affect risk checks and future New Analysis defaults.

## 45–65: Create an analysis

1. Open **New Analysis**. The latest published Workflow Lab graph is used
   automatically.
2. Choose the stock and analysis date.
3. Review the verified provider map.
4. In a chain with several sources, select one or more visible providers.
5. Choose specialist agents, research depth, and risk profile.
6. Choose the quick and deep AI models.
7. Choose report detail, output language, currency, and evidence freshness.

A provider appears only in chains supported by its verified capabilities. FRED
and Polymarket appear in Macro, not in Market or Fundamentals.

## 65–75: Check safety limits

1. Review maximum runtime.
2. Review maximum model calls and provider calls.
3. Review the token and parallel-node limits.
4. Keep degraded mode enabled only when optional branches may fail safely.
5. Select **Start customized real analysis**.

## 75–85: Watch agents work

1. Open **Agent Room** after starting the run.
2. Follow evidence collection and normalization.
3. Read each specialist agent output.
4. Follow the bull and bear debate, risk views, and manager decision.
5. Check retries, degraded branches, and failures when a node does not finish.
6. Open **Run History** to pause an active run. The current parallel node batch
   finishes before the checkpoint is saved.
7. Select **Resume from checkpoint** for a paused, failed, or interrupted run.
   Completed nodes do not run again. For an old live run, reconnect its saved
   data and AI providers first.
8. Use **Cancel** only when the run should not continue.

## 85–95: Read and export the report

1. Open **Reports**.
2. Select a date or saved run.
3. Read every analyst view, bull and bear case, and risk view.
4. Review the final decision, warnings, evidence sources, workflow version, and
   lineage.
5. Export the report as PDF or JSON when needed.

## 95–100: Customize the workflow

1. Open **Workflow Lab**.
2. Edit nodes or compatible edges.
3. Use Undo if needed.
4. Select **Save**, then **Validate**.
5. Fix every validation error before publishing.
6. Select **Publish**. The next New Analysis run uses the new version
   automatically.

## Troubleshooting

- Empty model choices: verify an AI provider and at least one model.
- Missing Macro providers: verify FRED, Polymarket, or Alpha Vantage.
- HTTP 403: the provider refused public access from this network.
- HTTP 429: the public provider rate limit was reached; try later.
- Alpha Vantage missing: enter a valid Alpha Vantage API key and verify it.
- Expired login: sign in again.
- No report: open Agent Room and inspect the failed or running node.
- Cannot resume an old run: reconnect and verify the providers named in the
  error, then try **Resume from checkpoint** again.
