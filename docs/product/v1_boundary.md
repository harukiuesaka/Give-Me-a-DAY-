# v1 Boundary

## v1 in one sentence

v1 delivers the full validate-then-operate sequence — from goal input to autonomous Paper Run — for investment strategies using public daily data, with automated stop conditions, monthly reporting, quarterly re-evaluation, and re-approval flows.

## v1 principle

**Narrow, deep, end-to-end.**

- **Narrow**: Investment strategies only. Japanese and US equities. Daily frequency. Public data sources. Single strategy at a time.
- **Deep**: Real backtests on real data. Real statistical tests. Real audit with 10 categories and 48 patterns. Real stop conditions that actually halt the system.
- **End-to-end**: The user types a goal and, after approval, has a strategy running in simulation. No code to write. No backtests to read. No infrastructure to build. No monitoring dashboard to watch.

If a feature makes the product broader but shallower, it stays out.
If a feature requires the user to analyze or build, it stays out.
If a feature skips validation for faster operation, it stays out.

## v1 in scope

### Internal pipeline (user does not interact with this)

| Component | Description |
|-----------|-------------|
| Goal interpretation | Parse natural-language goal into structured intent |
| Domain framing | Transform goal into testable research problem with falsifiable claims |
| Research spec compilation | Define objectives, assumptions, constraints, evidence needs, failure conditions |
| Candidate generation | Generate 3–5 strategy directions (baseline + conservative + exploratory minimum) |
| Public data acquisition | Acquire daily OHLCV, FRED macro indicators, CFTC COT, index constituents via free APIs |
| Data quality checking | Completeness, consistency, temporal, survivorship, point-in-time checks |
| User data ingestion | Accept CSV/JSON uploads for data not available via public APIs |
| Backtest execution | Run vectorized backtests on daily data. Max 20 years, max 500 instruments |
| Statistical testing | t-tests, bootstrap, multiple testing correction, ADF, cointegration |
| Candidate comparison | Compare candidates across 6 axes. Generate ranking with statistical significance tests |
| Audit / rejection | 10-category audit rubric with 48 issue patterns. Compound pattern detection. Automatic disqualification logic |
| Recommendation generation | Select Primary and Alternative from surviving candidates. Set confidence level mechanically |
| Re-evaluation trigger definition | Define stop conditions, re-evaluation schedule, re-approval conditions |

### User-facing

| Component | Description |
|-----------|-------------|
| Goal input screen | Single screen. Goal text (required) + success criteria, risk tolerance, time horizon, exclusions (optional) |
| Loading screen | Real-time progress indicators for internal pipeline steps |
| 2-candidate presentation | Primary (⭐) and Alternative (🔄) cards with: name, summary, expected return band, estimated max loss, confidence level, key risks (2–3), stop conditions summary |
| Presentation context | Validation summary (1 line), recommendation expiry, rejection summary (1 line), execution caveats |
| Approval screen | Selected candidate re-displayed, key risks re-displayed, full stop condition list, re-evaluation schedule, Paper Run notice (v1), risk confirmation checkbox, approve button |
| Paper Run status card | Single card: status indicator (🟢🟡🔴⏸), current value, stop condition proximity, next report date, next re-evaluation date |
| Monthly report | 3–5 sentence natural-language summary. Key numbers. Stop condition proximity. Next actions |
| Quarterly re-evaluation | Core Loop re-execution with fresh data. Result: continue / change candidate (re-approval required) / stop all |
| Re-approval flow | Triggered by stop condition hit, candidate change recommendation, or user request. Same flow as initial approval |
| Stop / resume controls | User can manually stop Paper Run at any time. Resume requires re-approval |
| Markdown export | Candidate presentation as downloadable Markdown file |

### Paper Run (v1 in scope)

| Component | Description |
|-----------|-------------|
| Daily cycle | Market data acquisition → signal calculation → virtual portfolio update → performance calculation → stop condition check → anomaly detection → result storage |
| Virtual capital | Default ¥1,000,000. User-adjustable at approval time |
| Rebalance frequency | Monthly (v1 fixed) |
| Cost model | Commission 10bps + spread 10bps (v1 fixed) |
| Execution timing | T+1 open (v1 fixed) |
| Stop conditions (system-defined, not user-configurable in v1) | Max drawdown -20%, 3-month consecutive underperformance vs benchmark, anomaly detection (signal 3σ deviation), data quality failure (3 consecutive days) |
| Stop behavior | Automatic halt + user notification. Resume requires re-approval |
| Monthly report | Auto-generated. Natural language + key numbers |
| Quarterly re-evaluation | Core Loop Steps 5–8 re-executed with fresh data |

### Notifications (v1 in scope)

| Trigger | Urgency | Channel |
|---------|---------|---------|
| Monthly report ready | Normal | Push + Email |
| Stop condition approaching (drawdown > -15%) | High | Push + Email |
| Stop condition hit (automatic halt) | Urgent | Push + Email |
| Quarterly re-evaluation complete (no change) | Normal | Push + Email |
| Quarterly re-evaluation (change recommended) | High | Push + Email |
| Anomaly detected (automatic pause) | Urgent | Push + Email |

## v1 out of scope

| Excluded | Reason | Target version |
|----------|--------|---------------|
| Real-money execution | Requires broker integration and regulatory considerations | v1.5 |
| Broker API integration | Dependency on third-party APIs and authentication flows | v1.5 |
| Live order placement | Paper Run must prove value before real execution | v1.5 |
| User-customizable stop conditions | Prevents users from disabling safety mechanisms. v1.5: strictening only | v1.5 |
| Paid data source integration | Cost and vendor contract complexity | v1.5 |
| Tick-level or intraday data | Data volume and computational requirements exceed v1 infrastructure | v2 |
| Custom stress test scenarios | Requires additional UI for scenario definition | v1.5 |
| Detailed analytics dashboard | Users should not need to analyze. They should receive conclusions | v1.5 (optional detail mode) |
| Multiple simultaneous strategies | Single-strategy focus preserves depth | v2 |
| Dynamic re-optimization during runtime | Adds complexity without proven need in v1 | v2 |
| Automatic re-approval | All re-approvals require explicit user confirmation in v1 | v2 |
| Cross-asset strategies | Requires cross-market data, correlation modeling | v2 |
| Multi-currency portfolio management | Adds FX risk layer | v2 |
| Regulatory compliance advice | Legal liability | Never |
| Performance guarantees | Impossible and dishonest | Never |
| PDF export | Markdown is sufficient for v1 | v1.5 |
| Generic business automation | Not this product | Never |
| No-code workflow builders | Not this product | Never |
| Broad "build anything" positioning | Not this product | Never |

## v1 expected user journey

```
1. User types goal                              (30 seconds)
2. System runs internal pipeline                 (5–10 minutes)
3. User sees 2 candidate cards                   (1 minute to review)
4. User approves one candidate                   (30 seconds)
5. Paper Run begins                              (automatic)
6. User receives monthly report                  (monthly, 1 minute to read)
7. System re-evaluates quarterly                 (automatic)
8. User re-approves if recommendation changes    (as needed)
```

Total active user time in v1: approximately 5 minutes at setup, 1 minute per month thereafter.

## v1 success criteria

v1 is successful if:

1. A user can go from goal input to running Paper Run in under 15 minutes (including pipeline execution time)
2. The internal pipeline genuinely rejects weak candidates (not all candidates pass)
3. Stop conditions actually halt the Paper Run when triggered
4. Monthly reports are generated on time and are comprehensible without investment expertise
5. Quarterly re-evaluation detects when market conditions have changed enough to warrant candidate replacement
6. The user never needs to write code, read a backtest, or build infrastructure

v1 is NOT successful if:

- All candidates always pass audit (audit is too lenient)
- No candidates ever pass audit (audit is too strict or pipeline is broken)
- Users need to interpret numerical results to make approval decisions
- Paper Run runs indefinitely without re-evaluation
- Stop conditions are never tested or never trigger
- The product feels like a research tool that requires expertise to use

---

**Role of this document**: This defines exactly what v1 includes and excludes. It is the authoritative boundary for implementation decisions. If a feature is not listed in "v1 in scope," it does not belong in v1 code. If a feature is listed in "v1 out of scope," it must not be implemented in v1 even if it seems easy to add.
