# NoraBT Ideal LLM Architecture

> **Status:** Implemented for the deterministic core; LLM layer still future work
> **Gate evidence:** `Agent/none/test/test_acceptance_gates.py` executes section 12
> **Scope:** LLM separation, backend/core contracts, report/UI stability
> **Product boundary:** Read-only analysis, interpretation and evidence presentation
> **Non-goal:** Trading, copying, pausing, closing or modifying a user's bot

---

## 1. Purpose

NoraBT is an evidence-first risk and behavioral analysis system for OKX bots.
Its quantitative engine is the source of truth. A future LLM layer may help a
user ask questions, select analyses and understand the result, but it must never
replace, alter or silently reinterpret the deterministic engine.

The permanent architecture rule is:

```text
Raw/public OKX data
        ↓
Normalization, reconciliation and data-quality checks
        ↓
Deterministic bot + market analytics
        ↓
Risk vectors, behavioral profile, scenarios and uncertainty
        ↓
Versioned analysis dossier
        ↓
Optional LLM analyst
        ↓
Human-readable report and read-only conversation
```

The LLM starts **only after the engine has finished the requested analysis**.
It is a post-analysis interpreter, not part of the computation path. If more
evidence or another scenario is needed, the user or a deterministic application
flow starts a new backend analysis first; the LLM sees that new completed result
only afterwards. It may not calculate a financial metric in prose or make a
decision for the user.

---

## 2. Product identity

NoraBT is not an autonomous trading agent. It is an:

> **Evidence-First Bot Intelligence and Market Risk Analyst**

The product helps a user understand:

1. what a bot appears to do;
2. how it earns and realizes returns;
3. how it handles losing positions;
4. which market and regime conditions were actually observed;
5. which conditions are untested or simulated;
6. how the bot may fail under explicit scenarios;
7. how strong each conclusion is; and
8. what the public data cannot establish.

The user remains responsible for any later decision. NoraBT must not expose a
trade, copy, pause, close, allocation or personalized investment instruction as
its product conclusion.

### Allowed language

- "The observed ledger shows..."
- "The data is consistent with..."
- "This pattern is inferred with medium confidence..."
- "Under this hypothetical scenario..."
- "This conclusion depends on..."
- "The available evidence cannot determine..."
- "The result is untested in..."

### Disallowed language in the public analyst result

- "You should copy this bot."
- "Buy, sell, stop or reduce this bot."
- "This bot is safe."
- "This bot will profit."
- "Guaranteed return/safety."
- A personalized allocation or risk instruction.

A legal disclaimer is not a substitute for this technical boundary. The
backend must make the prohibited output structurally unavailable to the LLM.

---

## 3. Permanent separation of responsibilities

### 3.1 Deterministic core owns truth

The backend owns all of the following:

- OKX data ingestion and normalization;
- identity and ledger reconciliation;
- observed versus inferred attribution;
- freshness, completeness and coherence;
- market features and regime classification;
- closed-book and open-book/deferred-loss metrics;
- equity and capital reconstruction;
- behavioral measurements;
- market compatibility measurements;
- Monte Carlo, bootstrap and stress scenarios;
- confidence, uncertainty and sensitivity;
- risk vectors and quality metrics;
- evidence references and limitations;
- deterministic claim eligibility.

The current foundations remain valid:

- `MarketResult` in `backend/market/schemas/market_result.py`;
- `BotResult` in `backend/mcp/schemas/bot_result.py`;
- ten QC lenses in `backend/qc/evaluator/lenses/`;
- the pipeline in `backend/pipeline.py`;
- the existing narrative safety boundary in `backend/qc/reporting/narrative.py`.

### 3.2 LLM owns interpretation and interaction

The future LLM may:

- interpret a completed analysis dossier;
- explain a completed dossier at different levels of detail;
- compare evidence-backed findings already present in the dossier;
- identify that the available evidence is insufficient;
- identify which pre-defined additional analysis the user may request next;
- explain the result after that separate backend analysis has completed;
- navigate the report and evidence graph.

The LLM may not:

- calculate or edit a metric;
- edit a risk score or verdict;
- change a confidence value;
- suppress a limitation;
- promote `INFERRED` or `SIMULATED` evidence to `OBSERVED`;
- invent an evidence reference;
- call a write/trading/execution tool;
- issue a personalized financial instruction.

### 3.3 UI owns presentation, not business logic

The React SPA and server-rendered report are views of the same versioned dossier.
They must not independently recompute risk, infer new labels, or parse a prose
paragraph to discover a number.

A future core update should normally change:

```text
analytics → dossier fields → report data adapter
```

It must not require rewriting the visual design or moving business logic into
`frontend/src` or `backend/web/report_page.py`.

---

## 4. Three execution modes

### Mode A — Direct deterministic report

For ordinary requests such as opening a known bot report:

```text
request → cached/versioned dossier → report
```

No LLM is required. This is fast, reproducible and cheap.

### Mode B — Read-only analyst request

For a question requiring several analyses:

```text
user question
  → LLM creates a bounded analysis plan
  → backend executes approved read-only analyses
  → dossier is rebuilt
  → claim/evidence verifier runs
  → LLM explains the verified result
```

The LLM does not receive authority to change the result.

### Mode C — LLM presentation only

This is the current narrative concept:

```text
completed metrics + fixed claims → LLM prose → strict validation → report
```

Mode C is optional and must continue to degrade safely to deterministic text if
the model is unavailable or fails validation.

---

## 5. Canonical backend contract: Analysis Dossier

The future core should publish one canonical object for API, MCP, web report and
LLM. The exact implementation can remain Pydantic, but the boundary should be
versioned and serializable.

```text
AnalysisDossier
├── identity
├── executive_essence
├── behavioral_dna
├── risk_vector
├── quality_vector
├── risk_twin
├── market_compatibility
├── failure_modes
├── scenarios
├── uncertainty
├── evidence_graph
├── claims
├── limitations
├── user_questions
└── methodology
```

The existing `BotRiskAssessment` remains a compatibility view during migration.
It should not remain the only source of truth once the dossier is introduced.

**Status:** every branch above is implemented and locked by
`test_acceptance_gates.py::test_dossier_carries_every_branch_of_the_section_5_contract`.
`scenarios` is the scenario laboratory; a second, thinner scenario list that
briefly lived beside it has been removed, so there is exactly one answer to any
scenario question. Each module that derives a published number records its own
`methodology_version` (`insights`, `scenarios`, `validation`, `evidence`)
alongside the existing `bot`/`market`/`qc` ones.

### Required dossier metadata

Every dossier must contain:

- `schema_version`;
- `analysis_id`;
- bot identity and unique code;
- `observed_at` and `generated_at` timestamps;
- evaluation mode (`SNAPSHOT` or `LIVE`);
- dataset/evidence hash;
- methodology version;
- code version or build identifier;
- simulation seed where applicable;
- source freshness status;
- reproducibility warnings.

### No hidden transformation

A consumer must be able to distinguish:

```text
OBSERVED   = directly present in a trusted source
INFERRED   = derived from observed data with an explicit method
SIMULATED  = generated under stated assumptions
UNKNOWN    = not established
```

No serializer, LLM or UI component may collapse these states into one generic
number without preserving the original status.

---

## 6. Dossier modules

### 6.1 Executive Essence

A concise, non-prescriptive answer visible to both admin and user:

- what the bot appears to do;
- dominant observed behavior;
- strongest positive evidence;
- strongest fragility;
- evidence reliability;
- the most important unknown.

This is not a buy/copy verdict. It is the shortest accurate description of the
bot's observed operating character.

### 6.2 Behavioral DNA

Behavioral DNA is a structured profile, not a label guessed from a bot name.
It should be built from the existing behavior detector and extended with:

- profit mechanism;
- win/loss holding-time asymmetry;
- loss realization behavior;
- position-size response after wins versus losses;
- leverage response after wins versus losses;
- re-entry behavior;
- profit concentration;
- directional bias;
- regime dependence;
- capital intensity;
- temporal stability;
- transparency and attribution quality.

Every trait needs:

- a measured value or bounded range;
- sample size;
- evidence status;
- supporting evidence IDs;
- counter-evidence IDs;
- caveats.

Use "martingale-like characteristics" only when the measured evidence supports
that wording. Do not infer a named strategy from a nickname or a single pattern.

**Status:** each trait reports the sample that actually supports it, not the
whole ledger. A trait measured on losing trades carries the loss count, a
regime trait the phase-labelled count, an open-position trait the position
count. Reporting the ledger count everywhere overstated confidence by several
times for exactly the traits the risk verdict leans on.

### 6.3 Risk Twin

Risk Twin shows three deliberately separate states:

1. **Reported state** — what closed trades show.
2. **Marked state** — what changes when currently open positions are marked to
   market.
3. **Stressed state** — what changes under a named scenario.

The report must show the transformation between states, not silently replace
one with another. The deferred-loss work already in the core is the foundation
for this feature.

**Status:** all three states are populated. The stressed states are taken from
the scenario laboratory rather than recomputed, so "stressed" means exactly one
thing wherever it appears.

### 6.4 Market Compatibility

Compatibility is conditional, never an absolute bot verdict. It answers:

- where the bot has actually traded;
- which regimes were observed;
- where the behavior was profitable or fragile;
- which conditions are untested;
- which results are historical, inferred or simulated.

Each matrix cell must carry:

- symbol and venue;
- market regime;
- observed trade count;
- outcome interval where available;
- drawdown/tail interval where available;
- reliability grade;
- failure modes;
- evidence references.

The current pipeline may continue to use one primary market for legacy QC
scoring. Compatibility analysis can use the resolved market coverage already
returned by `RiskSupervisionResult` without changing the legacy score.

### 6.5 Failure Mode Map

A failure mode describes a mechanism and its conditions, not a prediction that
failure will happen. Initial catalog:

- deferred-loss realization;
- persistent trend against accumulated exposure;
- liquidity contraction;
- leverage escalation;
- margin exhaustion;
- profit concentration;
- regime dependence;
- loss clustering;
- position concentration;
- funding drag;
- execution/slippage sensitivity;
- data opacity.

Each mode must show:

- mechanism;
- observed support;
- counter-evidence;
- trigger conditions;
- early indicators;
- affected metrics;
- assumptions;
- what evidence would falsify or weaken the finding.

**Status:** the full catalogue is implemented in
`Agent/backend/qc/reporting/insights.py::build_failure_modes`, and every mode
carries all eight fields. A mode appears only when a measurement puts it there,
and `observed_support` states that measurement. An absent mode means "not
observed", never "ruled out".

### 6.6 Scenario Laboratory

The current fixed-factor stress implementation is a valid prototype, but future
scenario results must identify their source and assumptions. Supported families:

- historical replay;
- market-quantile shock;
- position-specific price shock;
- volatility shock;
- liquidity/depth shock;
- spread/slippage shock;
- funding shock;
- regime transition;
- user-defined hypothetical scenario.

A scenario result must return ranges and reliability, not false precision:

```text
central estimate
lower/upper interval
affected positions or symbols
assumptions
coverage
failure modes triggered
invalid/missing inputs
```

### 6.7 Uncertainty Passport

Confidence must be decomposed into understandable components:

- identity confidence;
- ledger/reconciliation confidence;
- data completeness;
- freshness;
- instrument attribution;
- sample adequacy;
- regime coverage;
- extrapolation distance;
- parameter/seed stability;
- model agreement.

The dossier must be able to abstain from a stronger statement when the evidence
is too thin. An abstention is a successful result, not an engine failure.

### 6.8 Evidence Graph and Claims

A claim is a structured object, not merely a sentence:

```text
claim_id
claim_type
statement_key
strength
supporting_evidence
contradicting_evidence
assumptions
uncertainty
falsifiers
allowed_wording_level
```

This lets the report, MCP and future LLM use the same claim without generating
three subtly different conclusions.

---

## 7. Ideal LLM analyst contract

### Input

```text
user_question
bot_code or selected bot
optional market/symbol
optional scenario parameters
requested explanation depth
user role
```

### Analysis boundary

The initial analysis contract is selected by the deterministic application layer
from a fixed allowlist such as `FULL_BOT_ANALYSIS`, `MARKET_DEEP_DIVE`,
`POSITION_AUDIT` or `COUNTERFACTUAL_SCENARIO`. The LLM does not choose or invoke
calculation tools inside an active run.

If the LLM identifies missing information, it returns a structured request such
as:

```text
missing_evidence
suggested_analysis_profile
required_user_parameter
reason
```

The application may then run that profile as a separate backend job. The LLM
receives and explains the result only after the job is complete.

### Explanation input

The LLM receives:

- the completed dossier;
- structured claims;
- evidence references and statuses;
- limitations;
- approved terminology;
- user explanation depth.

It does not receive permission to alter the dossier.

### Explanation output

The output must include:

- plain-language interpretation;
- evidence references;
- uncertainty;
- limitations;
- unanswered questions;
- no prohibited action language.

No raw chain-of-thought is needed or should be shown. The UI should show an
observable analysis trace: plan, tools used, evidence found and validation
status.

### LLM failure behavior

If the LLM is unavailable, times out, hallucinates a number, invents an evidence
ID or violates terminology policy:

1. discard the LLM explanation;
2. keep the deterministic dossier;
3. render a deterministic fallback summary;
4. record the failure in telemetry;
5. never lower or change the quantitative result.

---

## 8. Report and UI contract

The report has three audiences/views but one canonical dossier.

### 8.1 Analyst Result — admin and user result

This is the primary, concise overview tab after the analysis is complete. It is
intended for both users and administrators; detailed evidence remains grouped
inside distinct sections of this tab rather than being merged with the other
two product tabs. It must be easy to
understand without sacrificing depth.

It should answer:

- What is this bot's operating character?
- What evidence supports that description?
- What is the most important hidden fragility?
- Which market/regime conditions are observed or untested?
- What happens under relevant scenarios?
- How certain is each finding?
- What cannot be determined from public data?

Recommended order:

```text
Essence → Behavioral DNA → Reported/Marked comparison
→ dominant findings → uncertainty → limitations → evidence
```

The Analyst Report does not contain a personalized action or an instruction to
copy, stop or modify a bot.

### 8.2 Premium Market

Premium Market is the second, separate tab and is the deep analysis of the market assets in which the analyzed
bot trades. It is not a second bot verdict.

It should contain:

- market structure and regime;
- volatility and trend state;
- liquidity/depth and expected impact;
- orderflow and derivatives context where available;
- funding/open interest;
- token/DEX security where applicable;
- market freshness and source quality;
- bot exposure to the asset;
- observed compatibility of the bot with this market;
- market-specific stress scenarios;
- unresolved or untested market conditions.

Market facts must come from `MarketResult` and market analysis modules. The
market view must not silently invent bot conclusions when bot evidence is absent.

### 8.3 Other & Position

Other & Position is the third, separate tab and is the general and detailed bot-level analysis.

**Other/general** contains:

- identity and data provenance;
- performance statistics;
- equity/capital reconstruction;
- drawdown and underwater behavior;
- quality/reconciliation status;
- trade distribution;
- methodology and limitations.

**Position** contains:

- open positions;
- instrument attribution status;
- long/short/net exposure;
- notional, margin and leverage;
- mark price and unrealized PnL;
- open-loss impact on capital;
- liquidation-distance data when available;
- observed versus inferred position fields.

**Trade analysis** contains:

- closed trade ledger;
- holding-time distribution;
- win/loss asymmetry;
- entry/exit and re-entry patterns;
- size/leverage response after losses;
- profit concentration;
- loss clustering;
- strategy/phase behavior.

The exact visual grouping may remain compatible with the current `report`,
`market` and `trades` panels. The important invariant is semantic separation:
market analysis must not be mixed with bot-position/trade mechanics.

### 8.4 Style invariant

If a new backend field needs to be shown:

1. add it to the dossier contract;
2. add a stable UI data adapter/selector;
3. render it using existing NORA X-DS tokens and component patterns;
4. add a tooltip/methodology entry if it is a derived metric;
5. add light/dark and mobile tests;
6. do not introduce a new color, card style, chart language or typography rule
   without updating the design system.

Core updates must not redesign the UI. UI updates must not recompute core
analytics.

---

## 9. Role and access contract

Role-based visibility is a presentation/access concern, not a different
calculation path.

```text
same AnalysisDossier
  ├── user view: Analyst Report, safe readable result
  └── admin view: Analyst Report + Premium Market + Other & Position + evidence
```

A user view may hide a panel or sensitive raw detail, but it must not receive a
less accurate score or a differently computed conclusion. Any hidden content
must be represented by a limitation such as `DETAIL_WITHHELD_BY_ROLE`, not by
silently dropping evidence from the core.

This migration is done. The server decides role scoping
(`Agent/backend/qc/reporting/view_policy.py`); `GET /bot/<code>?view=user`
renders the user-scoped document, and the SPA reads the resulting
`data-hidden-panels` attribute instead of deleting panels itself. A withheld
panel keeps its element and semantic id and carries a visible
`DETAIL_WITHHELD_BY_ROLE` notice, so withheld detail stays distinguishable from
detail that was never measured. SSR panel IDs and semantic anchors remain
compatibility contracts.

---

## 10. Stable API boundaries

### Backend to report

Prefer one serialized dossier endpoint/payload. Do not make the report call
individual lens internals.

### Backend to frontend

Use stable field names and explicit nullable values. Never use display strings
as machine identifiers.

```text
stable_id: behavioral.loss_realization_asymmetry
label: localized display label
value: numeric/range value
status: OBSERVED/INFERRED/SIMULATED/UNKNOWN
confidence: numeric or grade
evidence_refs: IDs
```

### Backend to LLM

Expose only read-only analyst tools. A tool result must be a schema-valid
fragment or dossier, not untrusted HTML.

### Legacy compatibility

Keep current v1 endpoints and report selectors while v2 is introduced. Add
contract tests that prove v1 consumers remain valid until migration is complete.

---

## 11. Development rules for future core updates

When improving precision, update only the relevant backend layers:

```text
source → analytics → dossier → tests
```

Do not modify the UI unless a new field genuinely needs to be visible.

When adding a visible field:

1. define its meaning and unit;
2. define its evidence status;
3. define its missing-data behavior;
4. define its confidence/interval;
5. define its methodology tooltip;
6. add it to the dossier;
7. update the data adapter;
8. use the existing UI style;
9. add regression tests.

When changing a methodology:

- increment `methodology_version`;
- preserve the old version for stored assessments where possible;
- record the migration/compatibility behavior;
- rerun OOS and regression validation;
- never silently reinterpret historical results.

When adding an LLM capability:

- add it outside deterministic analytics;
- define its allowed tools;
- define its prohibited outputs;
- validate structured output;
- add hallucination/number-lock tests;
- provide deterministic fallback;
- never let it write into the source-of-truth dossier.

---

## 12. Acceptance gates

### Core correctness

- [x] Every material claim has evidence references.
- [x] Observed, inferred and simulated values remain distinct.
- [x] Missing data cannot become a safe-looking value.
- [x] Reported, marked and stressed states remain distinct.
- [x] Scenario outputs contain assumptions and uncertainty.
- [x] Quantitative results are reproducible from dataset hash, methodology and seed.
- [x] Existing v1 tests remain green during migration.

Scenarios are built by `Agent/backend/qc/reporting/scenarios.py`: regime-,
execution- and deferred-loss-conditioned what-ifs, each resampled with the
engine's own stationary bootstrap so every result carries a percentile band
rather than a bare point estimate. A condition with too few observed trades is
reported as `INSUFFICIENT` and carries no numbers at all.

Out-of-sample behaviour is validated by
`Agent/backend/qc/reporting/validation.py`, which splits the observed ledger
chronologically and reports how far later windows depart from earlier ones. It
is a holdout validation of observed performance, not a strategy
re-optimisation -- NoraBT observes live bots and has no strategy object to
re-fit. The fold geometry and gate shape follow the walk-forward runner in the
sibling `nora` studio pipeline so both products grade stability the same way.

### LLM safety

- [x] LLM receives only a completed dossier or completed deterministic analysis result.
- [x] LLM is never invoked inside market/bot/QC calculations.
- [x] LLM cannot start or mutate an active calculation job.
- [ ] LLM cannot edit scores, verdicts, confidence or evidence status.
- [ ] LLM cannot call execution/trading tools.
- [ ] Unsupported claims are rejected.
- [ ] Numbers are locked to engine-provided values.
- [ ] Prohibited investment/action language is rejected.
- [ ] Model failure falls back to deterministic text.

The first three hold structurally: the dossier path imports no narrative module
(`test_dossier_isolation.py`), and the dossier builder takes a finished result
rather than a pipeline handle. The remaining items are properties of an LLM
layer that is not part of this work.

### Report/UI stability

- [x] Admin and user use the same core dossier.
- [x] Analyst Report is understandable without opening advanced panels.
- [x] Premium Market contains market/asset analysis only.
- [x] Other & Position contains bot/general/position/trade analysis only.
- [x] New fields use existing NORA X-DS styles and tokens.
- [x] No analytics logic is added to React or HTML rendering.
- [x] UI regression tests cover role visibility, panel IDs and semantic anchors.
- [x] Light/dark/mobile rendering remains valid.

`Agent/none/test/test_render_invariants.py` asserts the structural properties a
light/dark/mobile check exists to catch: every token used without a fallback is
defined, every dark override has a light value, charts scale by viewBox, no
block is pinned wider than a phone, and the viewport and colour-scheme are
declared. It found and fixed a real defect (the snapshot banner used four
tokens this design system does not define). It does not replace a visual
review of the rendered page.

---

## 13. Final architecture statement

NoraBT's long-term architecture is:

```text
Deterministic Quant Core = source of truth
Evidence Dossier          = canonical contract
LLM Analyst               = optional read-only interpreter/orchestrator
Report/UI                 = stable presentation layer
User                      = final decision maker
```

The LLM must make NoraBT easier to interrogate, not make the engine less
verifiable. The UI must make the result easier to understand, not become a
second analytics engine. Future precision work should therefore improve the
core dossier and preserve the report contract and design system.
