# Execution Layer

## What the Execution Layer is

The Execution Layer is everything in Give Me a DAY that touches real data and produces real results. It has two phases:

1. **Validation Execution**: Acquiring data, running backtests, and generating comparison results during the Core Loop (Steps 5–8). This happens once per run, before candidates are presented.
2. **Paper Run Engine**: Operating the approved strategy daily, monitoring stop conditions, and generating reports. This runs continuously after approval.

Without the Execution Layer, Give Me a DAY would output plans. With it, the system outputs results and then operates on them.

---

## Validation Execution

### Data Acquisition

**Purpose**: Turn EvidencePlan items from "required" into "available" by actually getting the data.

**v1 auto-acquisition targets**:

| Data | Source | Method |
|------|--------|--------|
| Daily OHLCV (equities, ETFs, indices) | Yahoo Finance API | yfinance library |
| Adjusted close prices (dividend/split adjusted) | Yahoo Finance API | yfinance with auto_adjust |
| FRED macro indicators (GDP, CPI, rates, VIX) | FRED API | fredapi library |
| CFTC Commitments of Traders | CFTC public data | requests + CSV parse |
| Index constituents (TOPIX, S&P 500) | Exchange public data | Web scrape / static files |
| Basic financial ratios (PER, PBR) | Yahoo Finance / public screens | yfinance |

**v1 does NOT auto-acquire**:
- Point-in-time financial databases (Compustat, Bloomberg) — requires paid subscription
- Alternative data (satellite, credit card, web traffic) — requires vendor contracts
- Analyst estimates / NLP sentiment scores — requires paid subscription
- Tick or intraday data — data volume exceeds v1 infrastructure
- 13F filings / detailed flow data — complex parsing, low frequency

**User data ingestion**: Users can upload CSV/JSON/Parquet. The system auto-detects format, maps columns to internal schema (with confirmation if ambiguous), and runs quality checks.

### Data Quality Checking

Every acquired dataset goes through 5 checks:

| Check | What it detects | Severity mapping |
|-------|----------------|-----------------|
| Completeness | Missing values, gaps in time series | >5% missing → warning, >20% → critical |
| Consistency | Price anomalies (zero, negative, ±50% daily), volume anomalies | Any → warning, systematic → critical |
| Temporal | Date range vs plan requirement, frequency gaps, timezone issues | Insufficient coverage → critical |
| Survivorship | Whether delisted securities are included in universe data | Missing delistings → critical (for universe-dependent strategies) |
| Point-in-time | Whether data is PIT, has publication dates, or is latest-only | none on FND/MAC/SNT/FLW → LKG-07 flag |

Output: DataQualityReport per evidence item. Critical issues affect `usable_for_validation` flag. Quality issues feed into Audit.

### Backtest Engine

**Architecture**:

```
BacktestEngine
├── UniverseBuilder         — construct PIT universe from metadata
├── SignalGenerator         — compute strategy signals per archetype
├── PortfolioConstructor    — build portfolios from signals + constraints
├── CostModel              — apply transaction costs
├── ExecutionSimulator      — simulate order execution with timing lag
└── MetricsCalculator       — compute performance and risk metrics
```

**Constraints (v1)**:
- Daily frequency only
- Max 20 years of history
- Max 500 instruments per universe
- Single-strategy evaluation (no portfolio-of-strategies)
- Monthly rebalance (fixed in v1)
- Cost model: commission 10bps + spread 10bps (fixed in v1)
- Execution timing: T+1 open (fixed in v1)

**Leakage prevention built into engine**:
- Signal generation uses only data available at signal date (enforced by data alignment layer)
- Universe construction uses point-in-time constituent lists where available
- Financial data uses publication date + buffer when PIT database is unavailable
- Look-ahead in any data access raises a runtime error, not a silent bias

**Metrics computed**:

| Category | Metrics |
|----------|---------|
| Return | Total return, annualized return, monthly returns series |
| Risk | Annualized volatility, max drawdown, VaR(95%), CVaR(95%) |
| Risk-adjusted | Sharpe ratio, Sortino ratio, Calmar ratio, Information ratio |
| Trading | Win rate, profit factor, average win/loss, annual turnover |
| Cost impact | Gross return, net return, cost drag (gross - net) |

### Statistical Testing

Automatic tests run on backtest results:

| Test | Purpose | Audit connection |
|------|---------|-----------------|
| t-test (return ≠ 0) | Is excess return statistically significant? | testable_claims Layer 1 falsification |
| Bootstrap p-value | Significance without normality assumption | Robustness check |
| Sharpe ratio significance | Is Sharpe distinguishable from zero? | OVF-06 detection |
| In-sample vs out-of-sample Sharpe | Overfitting detection | OVF-06 + testable_claims Layer 2 |
| Multiple testing correction (Bonferroni/FDR) | Adjust for testing multiple candidates/params | OVF-03 mitigation |
| ADF test | Stationarity of factor returns | ASM-02 verification |
| Engle-Granger cointegration | Pair relationship stability (STAT_ARB only) | STAT_ARB Layer 1 claims |

### Comparison Engine

After all candidates are backtested, the Comparison Engine produces a ComparisonResult:

- Normalizes all metrics to common scale (baseline = reference)
- Tests statistical significance of differences between candidates
- Detects dominance (one candidate beats another on all metrics)
- Generates execution-based rejection signals (disqualifying_failures breached)
- Produces ranking rationale per comparison axis

The Comparison Engine's output feeds directly into the Audit's execution-informed mode.

### Execution-informed Audit

When TestResults exist, the Audit adjusts severity based on actual data:

| Situation | Severity adjustment |
|-----------|-------------------|
| Out-of-sample Sharpe ≥ 50% of in-sample | overfitting_risk severity -1 |
| Out-of-sample Sharpe < 50% of in-sample | overfitting_risk severity +1 |
| Cost-adjusted net return > 0 | realism severity -1 |
| Cost-adjusted net return < 0 | realism severity → critical, disqualifying |
| All regimes show positive return | regime_dependency severity -1 |
| Worst regime return < -20% annualized | regime_dependency severity +1 |
| PIT compliance = full | leakage_risk severity -1 |
| PIT compliance = none on relevant data | leakage_risk severity remains or +1 |

When execution failed (data unavailable, backtest timeout), the Audit falls back to plan-based mode with a caveat added to the output.

### Validation Execution failure handling

| Failure | System behavior |
|---------|----------------|
| Data acquisition fails for some items | Continue with available data. Update coverage_metrics. Add caveats |
| Data acquisition fails for all items | Fall back to planning-only mode. confidence_label capped at low |
| Backtest times out (>300s per test) | Use partial results. Mark test as partial |
| Backtest engine error | Skip test. Mark as failed. Continue remaining tests |
| All backtests fail | Fall back to planning-only mode. confidence_label capped at low |
| Statistical test produces NaN | Report inconclusive. Do not treat as pass or fail |

The system always produces output. It never stops at an error. Partial results are better than no results.

### Confidence adjustment from execution

FC-02 base calculation (plan-based) is modified by execution results:

```
execution_modifier = 0
IF all disqualifying_failure tests passed: +1
IF out_of_sample Sharpe ≥ 50% of in-sample: +1
IF cost-adjusted net return > 0: +1
IF all regimes positive: +1

IF execution_modifier ≥ 3: upgrade planning confidence by 1 level (low→medium)
IF execution_modifier = 0 AND plan confidence ≥ medium: downgrade by 1 level
ELSE: keep planning confidence

HARD CEILING: high requires execution_modifier = 4 AND planning = medium
              Even then, recommendation_expiry is mandatory
```

With free/approximate data, confidence is capped at medium regardless of execution results. Caveats document this cap.

---

## Paper Run Engine

### Purpose

Operate the approved strategy autonomously in simulation. No real money. The Paper Run proves that the strategy behaves in real-time as the backtest predicted — or reveals that it doesn't.

### Daily Cycle

```
Every trading day at market close + 1 hour:

1. DATA ACQUISITION
   - Fetch latest daily OHLCV for universe
   - Fetch latest macro indicators if strategy uses them
   - Validate data quality (same checks as Validation Execution)
   - IF data quality failure for 3 consecutive days → SC-04 triggers

2. SIGNAL CALCULATION
   - Compute strategy signals using latest data
   - Compare signals to historical pattern
   - IF signal deviates > 3σ from historical distribution → SC-03 triggers

3. REBALANCE CHECK
   - IF today is a rebalance date (monthly for v1):
     - Generate target portfolio from signals
     - Calculate required trades
     - Apply cost model to trades
     - Execute virtual trades at T+1 open price (next day)

4. PORTFOLIO UPDATE
   - Mark-to-market all positions using latest prices
   - Update virtual_capital_current
   - Update total_return_pct
   - Update current_drawdown_pct

5. STOP CONDITION CHECK
   - SC-01: current_drawdown_pct ≤ -20%? → halt_and_notify
   - SC-02: 3 consecutive months underperforming benchmark? → halt_and_notify
   - SC-03: signal anomaly detected? → pause_and_notify
   - SC-04: data quality failure 3 consecutive days? → pause_and_notify
   - IF any condition breached:
     - Set status = halted or paused
     - Record in halt_history
     - Notify user within 1 hour

6. STORE
   - Save PaperRunState snapshot
   - Append to daily history (for monthly report generation)
```

### Monthly Report Generation

```
Within 3 days of each month end:

1. Aggregate daily history for the month
2. Calculate monthly_return_pct, benchmark_return_pct
3. Update cumulative_return_pct
4. Assess stop condition proximity
5. Generate natural-language summary (3–5 sentences)
6. Determine next_actions text
7. Create MonthlyReport object
8. Push notification + email to user
```

The monthly report is the user's primary touchpoint with the running system. It must be comprehensible without investment expertise. No charts. No metrics tables. Sentences.

### Quarterly Re-evaluation

```
Every 3 months from Paper Run start:

1. Set PaperRunState.status = re_evaluating
2. Re-run Core Loop Steps 5–8 with latest available data:
   a. Update EvidencePlans with new data availability
   b. Re-acquire public data (latest 20 years including recent months)
   c. Re-run backtests including the most recent period
   d. Re-run statistical tests
   e. Re-run comparison
   f. Re-run audit
   g. Re-generate recommendation
3. Compare new recommendation to current running candidate:
   a. IF same candidate is still best → outcome = continue
   b. IF different candidate is best → outcome = change_candidate
   c. IF no candidate passes → outcome = stop_all
4. Create ReEvaluationResult
5. Act on outcome:
   a. continue → resume Paper Run automatically, notify user (normal)
   b. change_candidate → pause Paper Run, present new candidates to user, require re-approval
   c. stop_all → halt Paper Run, notify user (urgent)
```

### Halt and Resume

**On halt** (stop condition breached):
1. All virtual trading stops immediately
2. No new positions are opened, no rebalancing occurs
3. Existing virtual positions are frozen (marked-to-market continues for reporting)
4. User is notified within 1 hour: which condition, current state, what to do
5. PaperRunState.status = halted, halt_history updated

**On resume** (user requests):
1. System presents current state + original candidate card
2. User goes through approval flow again (Step 10)
3. New Approval object is created
4. Paper Run resumes from current portfolio state
5. Stop conditions reset (e.g., consecutive underperformance counter resets)

### Paper Run data persistence

| Data | Retention | Purpose |
|------|-----------|---------|
| Daily PaperRunState snapshots | Indefinite | Monthly report generation, re-evaluation baseline |
| Virtual trade history | Indefinite | Audit trail, v1.5 real-execution comparison |
| Signal history | 90 days rolling | Anomaly detection (SC-03) |
| DataQualityReport (daily) | 30 days rolling | SC-04 detection |
| MonthlyReport objects | Indefinite | User access, re-evaluation context |

---

## Module Structure

```
ExecutionLayer
│
├── ValidationExecutionService
│   ├── DataAcquisitionModule
│   │   ├── PublicAPIClient (yfinance, fredapi, CFTC)
│   │   ├── UserDataIngestion (CSV/JSON/Parquet)
│   │   └── DataQualityChecker
│   │
│   ├── BacktestModule
│   │   ├── UniverseBuilder
│   │   ├── SignalGenerator (archetype-specific)
│   │   ├── PortfolioConstructor
│   │   ├── CostModel
│   │   ├── ExecutionSimulator
│   │   └── MetricsCalculator
│   │
│   ├── StatisticalTestModule
│   │   ├── ReturnSignificance (t-test, bootstrap)
│   │   ├── SharpeSignificance
│   │   ├── MultipleTestingCorrection
│   │   ├── StationarityTests (ADF)
│   │   └── CointegrationTests (Engle-Granger)
│   │
│   ├── ComparisonModule
│   │   ├── MetricsNormalizer
│   │   ├── StatisticalComparator
│   │   ├── RejectionDetector
│   │   └── RankingGenerator
│   │
│   └── ExecutionInformedAuditAdapter
│       ├── SeverityReassessor
│       ├── ConfidenceRecalculator
│       └── CaveatGenerator
│
├── PaperRunEngine
│   ├── DailyCycleRunner
│   │   ├── MarketDataFetcher
│   │   ├── SignalCalculator
│   │   ├── RebalanceManager
│   │   ├── PortfolioUpdater
│   │   └── StopConditionChecker
│   │
│   ├── AnomalyDetector
│   │   ├── SignalDistributionTracker
│   │   └── PositionConcentrationChecker
│   │
│   ├── ReportGenerator
│   │   ├── MonthlyReportBuilder
│   │   └── NaturalLanguageSummarizer
│   │
│   ├── ReEvaluationRunner
│   │   ├── CoreLoopReExecutor (Steps 5–8)
│   │   ├── OutcomeComparer
│   │   └── ReApprovalTrigger
│   │
│   └── NotificationService
│       ├── PushNotifier
│       ├── EmailNotifier
│       └── UrgencyRouter
│
└── DataStore
    ├── EvidenceStore (Parquet files, per-run)
    ├── TestResultStore (JSON, per-run)
    ├── PaperRunStore (daily snapshots, per-paper-run)
    └── ReportStore (MonthlyReport objects, per-paper-run)
```

### Technology Stack (v1)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Data acquisition | Python + yfinance + fredapi + requests | Free API clients, pandas integration |
| Backtest engine | Python + numpy (vectorized) | Performance for daily-frequency backtests |
| Statistical tests | scipy.stats + statsmodels + arch | Standard libraries, well-tested |
| Comparison engine | Python + pandas + numpy | Custom logic, no external dependency |
| Paper Run daily cycle | Python + cron (or scheduler) | Simple scheduling, no heavy orchestration |
| Data storage | Local Parquet files (evidence), JSON (results/reports) | No database needed in v1 |
| Notifications | Email (SMTP or SendGrid) + push (Firebase or OneSignal) | Standard notification infrastructure |
| Anomaly detection | scipy.stats (z-score tracking) | Lightweight, sufficient for signal monitoring |

---

## What v1 Execution Layer does NOT include

| Excluded | Reason | Version |
|---------|--------|---------|
| Real-money order execution | Requires broker integration, regulatory compliance | v1.5 |
| Broker API integration | Third-party dependency, authentication complexity | v1.5 |
| Intraday signal calculation | Requires streaming data, sub-second latency | v2 |
| ML model training/inference pipeline | Requires GPU, model versioning, serving infrastructure | v1.5 |
| Custom stress test scenario engine | Requires scenario definition UI | v1.5 |
| Advanced market impact model (Almgren-Chriss) | Implementation complexity without proven need in Paper Run | v1.5 |
| Real-time monitoring dashboard | Users should check monthly, not daily | v1.5 |
| Automatic re-evaluation trigger monitoring | v1 uses fixed quarterly schedule. Event-based triggers require market data streaming | v1.5 |
| Cross-asset execution | Multi-market data, FX hedging, correlation management | v2 |

---

**Role of this document**: This defines everything that executes in Give Me a DAY — from data acquisition through backtest execution to Paper Run daily operations. Implementation of the BacktestEngine, PaperRunEngine, and all supporting modules must conform to these specifications. If implementation introduces capabilities not defined here, they belong in v1.5 or later, not in v1.
