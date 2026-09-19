# OmniTrade AI: presentation scenario and speaking script

A complete Software Engineering course presentation in conversational English, based on the project code and documentation reviewed on 14 September 2026.

Allow approximately 30–40 minutes, including the demonstration. A shorter 15-minute route appears at the end. **On screen** tells you what to do; **Say** provides words you can speak naturally. Presenter notes are for preparation, not for reading aloud.

This script was prepared by reviewing the repository. Preparing it did not involve running the application, verifying external connections, or rerunning the tests.

## Before the presentation

- Run `docker compose up --build -d` from the project directory in advance. Check that you can sign in at `http://localhost:5173`. The local demo credentials documented in the README are `demo / demo`.
- Save and verify the required model and data connections in the current server session. Restarting the API can clear credentials held in memory, so check them again before presenting.
- Prepare one successful analysis using real providers, together with its PDF and JSON exports. If you use that saved report during the presentation, clearly identify it as an earlier run and show its date.
- For a straightforward demonstration, use AAPL, all four analysts, research depth 2, Balanced risk, English or Italian output, and USD. This is a software demonstration example, not an investment recommendation. Use providers and models that are actually available to you.
- Keep the form's default budgets and rehearse this exact configuration. External response times are variable.
- Validate and publish the workflow before the session. During the demonstration, repair any deliberately introduced errors before publishing again.
- Prepare the contracts, node catalog, validator, runtime, model service, and a related test in your editor. Links are listed at the end.
- Prepare the Use Case, Component, Sequence, State, and Deployment diagrams from the UML folder.
- Enter private credentials before sharing your screen. During the demonstration, show connection status and model names.

## 1. Introduction and the problem — about 2 minutes

**On screen:** Sign in and open **Overview**.

**Say:**

“Hi Professor. Today I'd like to walk you through OmniTrade AI with a complete example: from choosing the data sources and analysis process to getting a report we can inspect.

The problem is that information about a stock is spread across different places. We have prices and volume, company financial information, news, economic conditions, and sentiment. Some of that information might be outdated, some might conflict, and sometimes a provider simply doesn't respond.

Our application brings those inputs into a defined workflow. It processes the evidence, produces different analytical views, examines positive and negative arguments, evaluates risk, and creates a report. The user can customize the process and see where the result came from.

The scope is stock analysis and decision support. The application doesn't place orders, connect to a broker, or manage an actual investment account.”

**Show:** The five data branches, the process from Configure to Report, recent reports, and the button to start an analysis.

**Presenter note:** “Portfolio Manager” is the name of a decision role in this application. It does not mean the product manages a real portfolio.

**Transition:** “I'll start by setting up the inputs, then I'll show how we can change the analysis process itself.”

## 2. Connections: models and real data — about 3 minutes

**On screen:** Open **Connections**. Select an available provider, show the relevant model and connection settings, then demonstrate **Save session connection** and **Verify now**. If the connection is already configured, verify it without re-entering the secret.

**Say:**

“We have two types of connections here: model providers and data providers. Data providers supply financial evidence, while the language model helps produce the analytical explanations.

Entering a key alone isn't enough. The connection must be saved and verified before it becomes usable in the analysis form. If access is denied or the provider limits the request, the application shows an error.

The fields depend on the provider. We may need an API key, a compatible API address, a model ID, or provider-specific settings. For example, Bedrock also has an AWS region and allowed model IDs. If several models are available, I can later select separate quick and deep models.

Private connection credentials are held in API memory for the server session. They aren't stored in the analysis history or report.”

**On screen:** Show **Load available models** where applicable. Then show **Connect supported keyless sources** and the data connection statuses.

**Say:**

“Yahoo Finance and Polymarket have a keyless connection path. FRED and Alpha Vantage have their own settings. Reddit and StockTwits are optional public sources, and their public endpoints may reject access, so we don't assume they are available.

A provider is offered only for the roles it supports. For example, FRED and Polymarket are macro sources. We'll see the capability map in New Analysis.

If I select several verified providers for one role, they form a fallback chain. When an earlier provider fails, the next selected provider can be tried. Selecting several sources doesn't mean every response is automatically combined.”

**Also show briefly:** The **Remove** button, without removing a connection needed for the demo.

**Provider coverage:** The model catalog includes OpenAI, Gemini, Anthropic, xAI, DeepSeek, Qwen, GLM, MiniMax, OpenRouter, Mistral, Kimi, Groq, NVIDIA NIM, Azure OpenAI, Amazon Bedrock, Ollama, and compatible servers. You do not need to demonstrate each one or claim that all were tested today.

**If verification fails, say:** “This connection isn't available right now. That's a real example of handling an external dependency. I'll continue with an existing verified connection.”

## 3. Profile: customization that affects the analysis — about 2 minutes

**On screen:** Open **Profile**. Show the display name, default ticker, default models, and **Investment Policy**. Change one appropriate demonstration value and select **Save profile**.

**Say:**

“This page stores both form defaults and the investor's policy. The name and email are profile information; they don't affect the recommendation.

The investment horizon, experience level, maximum acceptable loss, maximum position size, and excluded sectors are inputs to the analysis. The horizon affects decision thresholds, the loss limit is used in risk checks, and the position limit affects the decision guidance. Experience level is included in the instructions for explaining the result.

If the company's sector is excluded, the application's rules can block a BUY result. So these preferences affect the actual workflow behavior.

The policy is copied into each run. Later, we can identify the settings that were used to create a particular report.”

**To demonstrate an effect:** Prepare two reports with different policies and compare their settings, explanations, and warnings later. A changed setting does not necessarily turn BUY into SELL: it may change a threshold or explanation while the final action remains the same.

## 4. Workflow Lab: explain the complete process — about 3 minutes

**On screen:** Open **Workflow Lab**, show the complete graph, then zoom into its branches.

**Say:**

“The analysis process is represented as a graph. Each node has a specific responsibility, and each connection carries a particular kind of input or output.

First, the application resolves the stock symbol. Then we have five evidence branches: market data, fundamentals, news, macro, and sentiment. The data is normalized into common contracts. Technical indicators and fundamental ratios are calculated as well.

The evidence is collected at a join and passes through the time and quality checks. The selected specialist analysts then produce their views. There are four specialist analyst choices; macro is an evidence branch in this design, not a fifth analyst checkbox.

Next, the research stage considers the bull and bear cases and manages a bounded debate. The number of rounds is limited. After that, the application builds a proposal, evaluates aggressive, balanced, and conservative risk views, validates the decision, and produces the report.

This graph is an executable definition of the process.”

**Presenter note:** The reference graph in `sample_workflow.py` has 33 nodes. Customized graphs can have different counts. Node types, node instances, and reasoning roles are different things.

## 5. Edit the graph and demonstrate invalid cases — about 4 minutes

**On screen, in this order:**

1. Select a node. Show its type and **What this node does** description.
2. Rename it to **Market review for demo**, change its color, and click **Apply name/color**.
3. Move the node, then demonstrate **Undo** and **Redo**. Ctrl+Z and Ctrl+Y are also available.
4. Show **Smart next nodes** and explain that suggestions come from compatible port types.
5. Attempt to connect **Fetch Market** directly to **Report Renderer**. Their port types are incompatible. Expect a message rejecting the connection; the edge should not enter the graph.
6. Add a second **Start** node from the catalog and click **Validate**. Expect a start-count error, possibly accompanied by an unreachable-node error. Undo the addition and validate again.
7. Introduce **Delete** and **Reset node**. If you use them, undo the change. Reset node restores its name and color; it is not a reset of every execution parameter.
8. **Save**, **Validate**, and **Publish** the corrected graph. Show that it is valid.

**Say:**

“There are two levels of checking. An incompatible connection is rejected immediately in the editor. But checking one connection isn't enough to validate the complete workflow. We also need to check the start and end nodes, reachability, required inputs, loops, and budgets.

The error I just introduced was intentional. It shows how the application handles an incomplete process definition. Validation issues have a code and, where relevant, a node or edge identifier.

Save stores the draft. Validate checks the current definition. Publish creates the version that can be executed. Each run remains linked to its own published version, so a later draft edit doesn't redefine an old report.”

**Also cover briefly:** Adding nodes from the catalog and suggestions, deleting edges, the MiniMap, and zoom controls. A compatible suggested connection does not guarantee that the entire graph is valid.

**Reset graph:** Explain that this restores the complete default draft while preserving published versions and previous reports. The application displays its own confirmation dialog.

**Important implementation boundary:** The current editor supports node names, colors, positions, addition, deletion, and connections. Internal fields such as `failure_policy`, per-node timeout and retry, and `join_policy` exist in the contracts and engine, but the current Workflow Lab does not expose a general editor for all of them. Explain those fields in the code section.

## 6. New Analysis: cover all run settings — about 4 minutes

**On screen:** Open **New Analysis**. Show its four sections, the defaults loaded from Profile, and the published workflow label.

**Say:**

“Now I'll create an analysis using this workflow. The form automatically uses the latest published graph. These options customize this particular run.”

| Setting | What to say | What to demonstrate |
|---|---|---|
| Stock ticker and Analysis date | “I choose a supported stock symbol and the reference date for the analysis.” | AAPL and a valid date. A date field does not make this a complete backtesting system. |
| Verified provider map | “This shows which roles each connected provider supports.” | Point to one provider and its capabilities. |
| Five provider chains | “I can select compatible sources for market, company, macro, news, and sentiment evidence.” | Select an additional provider if available. The chain follows selection order; there is no separate reorder control. |
| Specialist branches | “Only the selected specialist analysts are used in this run.” | Temporarily deselect one, then restore it for the complete demo. |
| Research depth | “The research process is bounded between one and five rounds.” | Choose 2. |
| Risk profile | “The decision policy can be conservative, balanced, or aggressive.” | Choose Balanced. The selected policy is distinct from the three risk views in the workflow. |
| Allow degraded results | “An optional branch can fail while the application still produces a report with warnings.” | Enable it. It does not permit invalid core evidence. |
| Model provider | “I choose from verified model providers.” | A fixed display is expected when only one provider is available. |
| Quick and deep models | “Specialist analysis uses the quick model; research and risk stages use the deep model.” | Show available models. They can be the same model. |
| Reasoning effort | “Low, medium, or high is included in the analysis instructions.” | Choose Medium. Do not describe it as exact control over every model's internal reasoning steps. |
| Temperature | “Where the provider supports it, this adjusts response variation. Leaving it empty uses the provider default.” | Leave empty or use a rehearsed value. The form range is 0–2. |
| Model retries | “The model error-handling path has a limited retry setting.” | Choose 2. The form range is 0–5. |
| Report detail | “The report can be Summary, Standard, or Detailed.” | Choose Standard or Detailed. |
| Output language | “I can choose the language of the generated text.” | Choose English or Italian. Persian is not currently listed. |
| Base currency | “The supported base currencies are USD, EUR, GBP, and JPY.” | Use USD for a simple demo, or show a prepared EUR conversion report. |
| Evidence freshness | “I can set how recent the evidence needs to be, in hours.” | Choose 72. The form range is 1–720 hours. |
| Runtime seconds | “The analysis has a configured runtime limit.” | Default 900; form range 10–1,800 seconds. |
| Model calls and Provider calls | “We also configure limits on calls to external services.” | Both default to 30. Form ranges are 0–100 and 0–200 respectively. |
| Token budget | “The engine also has a token budget setting.” | Default 40,000. Do not present this as an exact provider billing meter. |
| Parallel nodes | “This limits how many nodes can execute together.” | Default 8; form range 1–32. |

**Say:**

“Valid individual values aren't enough. Their combination also needs to work with the graph. For example, a deeper research process with a very small model-call budget can be rejected before execution. We want configuration problems to be visible before expensive work starts.”

**On screen:** Click **Start customized real analysis**.

**Language coverage:** English, Italian, Chinese, Japanese, Korean, Hindi, Spanish, Portuguese, French, German, Arabic, and Russian. Output language is separate from interface localization.

**Data mode:** Recorded evidence is a testing mechanism. It is not offered as a normal analysis option in the production Docker interface.

## 7. Agent Room: follow execution — about 3 minutes

**On screen:** Show **Agent Room**, the run status, analyst cards, and **Collaboration timeline**.

**Say:**

“Here we can follow the analysis while it runs. We can see which stage has started, which has produced a result, and which is still waiting for its inputs. The timeline is built from workflow events.

Independent branches can run together within the configured concurrency limit. A dependent stage waits for its required inputs. For example, an analyst shouldn't start before the required evidence is available.

The bull and bear views make the research stage examine competing arguments. The risk stage then checks the proposal against the selected policy.”

**Implementation note for technical questions:** The backend provides an SSE endpoint, but the current Agent Room component refreshes activity through polling approximately every 800 milliseconds. Do not describe the page as directly consuming SSE.

The current progress calculation uses a 33-node reference count. It is not an exact progress measure for every customized graph or repeated debate round. The role cards also use a fixed list; events and report data provide further detail for customized workflows.

**If the run takes time, say:** “The run is still waiting for an external response. While it continues, I'll show the pause and recovery controls.”

## 8. Run History: pause, resume, and cancel — about 2 minutes

**On screen:** Open **Run History**, select the active run, and click **Pause**. Wait for **paused**, show **Inspect checkpoint**, then select **Resume from checkpoint**.

**Say:**

“Pause is cooperative. The request is recorded, and the engine stops at a safe boundary after the active batch finishes and a checkpoint is saved. It doesn't instantly interrupt an external request halfway through.

When the run resumes, the completed node outputs recorded in the checkpoint are retained, and unfinished work continues. This matters for longer analyses and worker interruptions because successful stages don't all need to restart.

Cancel is different: it ends the run permanently. A cancelled run can't be resumed. Resume is available for eligible states such as paused, failed, and interrupted.”

**Demonstrating cancellation:** Use a separate test run, or explain the button without cancelling the main run needed for the report.

**If the run finishes before you pause:** Show a prepared paused run or the controlled recovery evidence. Do not claim to pause a run that has already finished.

## 9. Reports: inspect the result and its evidence — about 3 minutes

**On screen:** Select **Open report**, or open **Reports**. Show the calendar, a date with saved reports, and the selected report.

**Say:**

“Reports are stored and can be found by date. At the top, we have the decision and confidence score, followed by the explanation and supporting material.

Each analyst has a viewpoint, main observations, and risks. In the bull and bear section, there are two separate measures. Support represents support for that direction. Evidence confidence represents confidence in the underlying evidence. Those are different concepts, and neither should be read as a guaranteed probability of profit.

We can also read the risk views and the final decision rationale. If evidence was excluded or the run was degraded, we should inspect the warnings.

Run settings show which analysts, risk policy, and research depth were used. For more detailed auditing, we can inspect evidence references and lineage in the structured output and checkpoint view.”

**On screen:** Find one evidence reference in the report. Locate the corresponding reference or related node and provider information in JSON or **Inspect checkpoint**. Download **PDF** and **JSON**.

**Say:**

“The PDF is useful for reading and presenting. JSON is useful for structured inspection and further processing. Version and hash information help us trace the output and check content integrity. A hash doesn't establish that the financial interpretation is correct.”

**Customization comparison:** Open two prepared reports one at a time and compare their settings, text, and warnings. The current interface does not provide a separate side-by-side comparison tool.

**Export boundary:** The backend supports HTML output, but the current Reports page exposes PDF and JSON buttons. Evidence details are not all individual clickable drill-down controls in the report page.

## 10. Demonstrate controlled failure and recovery — about 2 minutes

**On screen:** Open the defense scenario script, then the existing defense summary JSON. Run the script again only in a prepared, rehearsed environment: it overwrites the defense evidence files.

**Say:**

“We also have a controlled failure scenario, so we don't have to wait for an external service to fail randomly during testing.

This script simulates a market-provider timeout, failure of an optional sentiment source, and a worker interruption at the proposal stage. It then resumes execution from a checkpoint.

This is a software resilience test using controlled data. It is separate from the real-provider analysis I demonstrated.

In the existing evidence file, the final status is degraded, with 126 events, 18 checkpoints, and a resume from checkpoint 12. The recorded degradation reason is the simulated sentiment failure. If we rerun the script, the newly generated output is the evidence for that execution.”

**Explain evidence-quality failures:**

“Future evidence is rejected. Stale core market or fundamental evidence can't bypass the time checks just because degraded results are allowed. When policy permits, stale news, sentiment, or macro evidence can be excluded, with a warning, while the remaining process continues.”

## 11. Architecture and UML — about 3 minutes

**On screen:** Show the Use Case diagram, then Component or Deployment, followed by Sequence. Connect each diagram to something already demonstrated.

**Say:**

“Now let's connect the demonstration to the software design.

In the Use Case diagram, the user configures connections and the process, starts an analysis, follows execution, and reads the report. External data and model providers are outside the product boundary.

The interface uses React and TypeScript, and the API uses FastAPI. The workflow service owns execution. The evidence service handles evidence processing. The model gateway separates provider-specific model communication, and the report service prepares the output.

PostgreSQL stores durable information. Redis Streams carries events and supports distributed control coordination. The implementation also uses internal HTTP calls between services.

The Compose deployment contains eight main services: frontend, API, workflow, evidence, model gateway, report, PostgreSQL, and Redis. They are managed together.

The separation makes responsibilities and contracts explicit. For example, changing a data-provider adapter should not require rewriting the scheduler.”

**For the Sequence diagram, say:** “This shows the interaction from the user's request through evidence processing, analysis, events, and the final report.”

**For the State diagram, say:** “The running, paused, interrupted, failed, degraded, and cancelled states we saw in the interface are part of the execution contract. The UI is displaying application state.”

## 12. Code walkthrough: explain the custom implementation — about 4 minutes

**On screen:** Open the following code in order. Navigate to the relevant symbol instead of scrolling through entire files.

### A. Contracts and node catalog

**Say:**

“The contracts define WorkflowDefinition, NodeDefinition, Run, Budget, Checkpoint, and the event structures. The node catalog defines the inputs, outputs, and characteristics of each node type. The editor's connection suggestions are based on that information.”

### B. WorkflowValidator.validate

**Say:**

“This is where we can connect the earlier demo errors to the implementation. The validator checks the start and end counts, ports, reachability, unbounded cycles, required inputs, and budgets.

The cycle check uses indegrees and graph traversal. The application complexity comes from making these constraints work together and returning useful errors.”

### C. WorkflowRuntime.execute

**Say:**

“The runtime calculates which nodes are ready. It sorts the ready set, limits the batch with max_parallel_nodes, executes it with asyncio.gather, and saves a checkpoint.

Readiness and input ordering are controlled. That doesn't mean a language model always returns identical text, or that every concurrent event always arrives at the same time.”

### D. model_execute and merge_model_narrative

**Say:**

“This is the boundary between our application logic and the language model. The application first creates a structured draft. The model receives that draft and its evidence and improves the explanations. During merging, important fields such as action, confidence, and evidence references are protected in the relevant path.

In this implementation, the main decision fields and scores come from deterministic application logic. The model contributes narrative analysis within that structure.

The name deterministic_executor doesn't automatically mean fake data. The real-data path obtains evidence through the evidence service and applies shared processing logic to it.”

### E. A matching test

**Say:**

“Here is a test for the graph rule we just discussed. Removing Start should produce START_COUNT. Setting the loop bound to 50 should produce UNBOUNDED_LOOP. The test makes the expected behavior explicit.”

**Explain ownership:**

“React Flow, FastAPI, Redis, the database, the model, and formulas such as RSI are supporting tools or established calculations. Our main implementation work is the graph rules, scheduling, failure policies, bounded research coordination, configuration handling, recovery, and tracing evidence into the report.”

## 13. Requirements, development process, verification and validation — about 2 minutes

**On screen:** Show the requirements, traceability, XP selection, and verification-validation documents.

**Say:**

“We separate user requirements, functional requirements, and non-functional requirements. UR describes the user's need, FR describes observable system behavior, and NFR describes measurable quality.

For example, continuing an interrupted analysis connects a recovery requirement to checkpoint design, runtime code, and recovery tests. The traceability document records those relationships.

The project's documented development process is Agile with XP practices: small changes, tests, refactoring, and continuous integration. Working feedback matters because provider behavior, interface needs, and failure cases become clearer as the system is used. The documentation needs to evolve with those changes.

Verification asks whether the implementation follows its contracts and design. For example, does an invalid graph get rejected, and are checkpointed successful nodes preserved after resume?

Validation asks whether the integrated product meets the user's needs. The complete connection-to-report journey is one way to examine that.

The test suite includes unit, property, API, integration, and browser tests. CI uses controlled data and model behavior; live-provider checks are separate. The configured minimum coverage gate for the workflow core is 80 percent.”

**Be precise about recorded results:** The implementation-evidence document records 222 backend tests, 17 frontend tests, and approximately 89% workflow-core coverage on 28 August 2026. The defense verification JSON is dated 9 August and contains older figures. Say “According to this dated verification record,” rather than claiming the tests just passed. A fresh claim requires fresh execution output.

Do not invent a Red/Green history, working hours, or individual contributions without actual evidence.

## 14. User guide and closing — about 1 minute

**On screen:** Open **How to Use**, expand one section, and show the guide that can be opened or downloaded. Return to Overview or the final report.

**Say:**

“The application also includes a step-by-step user guide, covering setup, connections, analysis, reports, and recovery.

Today we configured the sources, edited the workflow, caught an intentional error, started an analysis, and followed the process into a report. The central aim is to make that process configurable, observable, and recoverable.

The current version has clear limits. Providers and models depend on external availability, model text can vary, and some engine parameters don't yet have editing controls in the interface. The product focuses on stock decision support.

Thank you, Professor. I'm happy to go into more detail on the validator, scheduler, or recovery implementation.”

## Likely questions and ready-to-say answers

| Question | Answer |
|---|---|
| How is this different from sending a prompt to ChatGPT? | “The application manages typed evidence, a versioned process, several roles, quality checks, execution limits, checkpoints, and lineage. The output is produced within that controlled software workflow.” |
| What did you implement yourselves? | “The validator, scheduler, failure and budget coordination, recovery, research and risk coordination, and report traceability. Supporting libraries are identified separately in the reuse register.” |
| Does the LLM decide the action itself? | “In the current implementation, the structured draft and main decision values come from application logic. The model improves the narrative, while fields such as action and confidence are protected during merging.” |
| What happens if a data API fails? | “Retries and fallback operate within the selected chain. Missing required evidence can fail the run; an allowed optional loss can produce a degraded report with warnings.” |
| What if the model returns invalid JSON? | “There are bounded attempts to obtain valid output. If formatting remains invalid, the current path can retain the application's draft. Network failures have their own retry and failure behavior.” |
| Does resume guarantee no external request is ever repeated? | “Completed nodes stored in a checkpoint are retained. Work interrupted before checkpointing may repeat, so we don't claim exactly-once execution for every external call.” |
| Does publishing change an old run? | “Drafts and published versions are separate. A run remains associated with its saved version and settings.” |
| Does deterministic mean the AI output is always identical? | “No. It describes controlled scheduling and application rules. Live data and generated explanations can vary.” |
| Is confidence the same as accuracy? | “No. A report score isn't a measured prediction-accuracy result or a probability of profit.” |
| Have you proven financial prediction accuracy? | “The current tests verify software behavior. Predictive accuracy and profitability require a separate financial evaluation.” |
| Why separate services? | “They make responsibilities, contracts, and failure boundaries explicit. The trade-off is more coordination and recovery complexity. This deployment is managed with one Compose setup.” |
| What security mechanisms exist? | “The application authenticates users, checks resource ownership, and keeps connection credentials out of durable analysis records. That isn't equivalent to a complete security audit.” |
| Does changing a node's name or color change the analysis? | “Those changes improve readability. Connections, branch selection, and execution policies affect behavior.” |
| Does selecting an output language translate the interface? | “No. It selects the generated text language. The actual report text still needs to be inspected.” |

## If the demonstration does not go as planned

| Situation | Action or wording |
|---|---|
| An external provider does not respond | Show the error. Continue with another verified connection, or introduce a saved report with its date. |
| Analysis is still running | Present architecture, code, or requirements, then return to the run. |
| The graph remains invalid after editing | Undo, validate, and publish. If necessary, use Reset graph, understanding that it resets the draft. |
| The session expires | Sign in again and check the connection statuses. |
| No model is available | “The live model stage isn't available right now. I'll show the saved execution and controlled tests separately.” |
| The result or PDF differs from rehearsal | Describe the actual output. Do not promise a particular action, profit, or translation quality in advance. |

## Short 15-minute route

| Time | Demonstration |
|---|---|
| 0–1 minutes | Overview: problem and scope. |
| 1–3 minutes | Connections and Profile: one verified connection and one policy. |
| 3–6 minutes | Workflow Lab: process, name/color edit, invalid connection, validate and publish. |
| 6–8 minutes | New Analysis: four configuration sections and Start. |
| 8–10 minutes | Agent Room and pause/resume if a run is active. |
| 10–12 minutes | Report, support versus confidence, evidence, PDF and JSON. |
| 12–14 minutes | Validator, runtime, the LLM boundary, and a matching test. |
| 14–15 minutes | Requirements, limitations, and closing. |

If execution takes longer, explicitly introduce a previously saved report. Keep the complete configuration table available for questions.

## Files to have ready

| Topic | File or folder |
|---|---|
| Requirements | [requirements.md](D:/PROJECT/OmniTrade/docs/requirements.md) |
| Requirement-to-code/test links | [traceability.md](D:/PROJECT/OmniTrade/docs/traceability.md) |
| Custom features and reused tools | [feature-categories.md](D:/PROJECT/OmniTrade/docs/feature-categories.md), [reuse-register.md](D:/PROJECT/OmniTrade/docs/reuse-register.md) |
| Custom application logic | [complex-custom-logic.md](D:/PROJECT/OmniTrade/docs/complex-custom-logic.md) |
| Architecture and decisions | [system-design.md](D:/PROJECT/OmniTrade/docs/system-design.md), [ADRs](D:/PROJECT/OmniTrade/docs/adr) |
| XP and implementation evidence | [xp-selection.md](D:/PROJECT/OmniTrade/docs/agile/xp-selection.md), [implementation-evidence.md](D:/PROJECT/OmniTrade/docs/agile/implementation-evidence.md) |
| Verification and validation | [verification-validation.md](D:/PROJECT/OmniTrade/docs/verification-validation.md) |
| Domain contracts | [contracts.py](D:/PROJECT/OmniTrade/omnitrade/contracts.py) |
| Typed node catalog | [catalog.py](D:/PROJECT/OmniTrade/omnitrade/engine/catalog.py) |
| Graph validator | [validator.py](D:/PROJECT/OmniTrade/omnitrade/engine/validator.py) |
| Scheduler and checkpoints | [runtime.py](D:/PROJECT/OmniTrade/omnitrade/engine/runtime.py) |
| Decision rules and evidence time checks | [executors.py](D:/PROJECT/OmniTrade/omnitrade/engine/executors.py) |
| Model/application boundary | [services.py](D:/PROJECT/OmniTrade/omnitrade/services.py) |
| Connections and providers | [connections.py](D:/PROJECT/OmniTrade/omnitrade/connections.py), [providers.py](D:/PROJECT/OmniTrade/omnitrade/providers.py) |
| API, versions, and run preparation | [api.py](D:/PROJECT/OmniTrade/omnitrade/api.py), [storage.py](D:/PROJECT/OmniTrade/omnitrade/storage.py) |
| Report generation | [reporting.py](D:/PROJECT/OmniTrade/omnitrade/reporting.py) |
| Reference graph | [sample_workflow.py](D:/PROJECT/OmniTrade/omnitrade/sample_workflow.py) |
| Graph and runtime tests | [test_validator.py](D:/PROJECT/OmniTrade/tests/test_validator.py), [test_runtime.py](D:/PROJECT/OmniTrade/tests/test_runtime.py) |
| Configuration tests | [test_configuration_matrix.py](D:/PROJECT/OmniTrade/tests/test_configuration_matrix.py) |
| Browser journey | [defense.spec.ts](D:/PROJECT/OmniTrade/frontend/e2e/defense.spec.ts) |
| Controlled failure scenario | [run_defense_scenario.py](D:/PROJECT/OmniTrade/scripts/run_defense_scenario.py) |
| Recorded failure evidence | [summary.json](D:/PROJECT/OmniTrade/artifacts/defense/summary.json) |
| UML diagrams | [uml-v7](D:/PROJECT/OmniTrade/modeling/visual-paradigm/uml-v7) |
| Deployment | [docker-compose.yml](D:/PROJECT/OmniTrade/docker-compose.yml) |

## One-line rehearsal cue

Login → problem → connections and verification → profile → workflow → edit and intentional error → validate/publish → analysis settings → Agent Room → pause/resume → report and evidence → export → controlled failure → UML → custom code → tests and requirements → limitations → closing.
