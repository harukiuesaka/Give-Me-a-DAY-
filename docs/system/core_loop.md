# Core Loop

## What the loop is

The Core Loop is the internal engine that transforms a user's investment goal into a running Paper Run. It is not a conversation. It is not a recommendation report. It is a pipeline that ends with an operating system.

```
Goal → Frame → Spec → Candidates → Evidence → Validation → Audit → Recommend → Present → Approve → Operate
```

The user interacts at three points: Goal (input), Present (review), Approve (commit). Everything between Goal and Present is invisible to the user. Everything after Approve is autonomous.

## Loop architecture

```
[1] Goal Intake             ← user input
[2] Domain Framing          ← internal
[3] Research Spec            ← internal
[4] Candidate Generation     ← internal
[5] Evidence Planning        ← internal + data acquisition
[6] Validation Execution     ← internal + backtest execution
[7] Audit / Rejection        ← internal
[8] Recommendation           ← internal
[9] Candidate Presentation   ← user sees 2 cards
[10] Approval Gate           ← user commits
[11] Paper Run Runtime       ← autonomous operation
[12] Re-evaluation           ← periodic, loops back to [5]
```

Step 7 feedback loop: If all candidates are rejected, the loop returns to Step 4 once, adding rejection reasons as constraints. If all candidates are rejected again, Step 8 produces a "no valid candidate" recommendation and Step 9 presents 0 cards with alternative directions.

---

## Step 1: Goal Intake

**Input**: User's natural language text + optional preferences
**Output**: UserIntent object
**User interaction**: Yes (single input screen)

The user types what they want. The system extracts: raw_goal, success_definition (if provided), risk_preference, time_horizon_preference, must_not_do. Missing fields get defaults and are recorded in open_uncertainties.

This step asks the minimum needed to start the pipeline. It does not ask for data availability (the system acquires data itself), automation preferences (v1 behavior is fixed), or detailed parameters (the system decides these internally).

---

## Step 2: Domain Framing

**Input**: UserIntent
**Output**: DomainFrame object
**User interaction**: None

The system classifies the goal into a strategy archetype (FACTOR, STAT_ARB, EVENT, MACRO, ML_SIGNAL, ALT_DATA, HYBRID, UNCLASSIFIED) and transforms it from "I want to build X" into "Is it verifiable that X works under conditions Y?"

The key output is `testable_claims` — a set of falsifiable assertions decomposed into three layers:
- Premise: Does the effect statistically exist?
- Core: Is it stable and large enough to exploit?
- Practical: Does profit survive after costs and constraints?

Each claim has a `falsification_condition` — what data would disprove it. Claims without falsification conditions are rejected.

`regime_dependencies` must be non-empty. Every investment strategy depends on market regime. The system forces at least market trend direction and volatility environment.

---

## Step 3: Research Spec Compilation

**Input**: UserIntent + DomainFrame
**Output**: ResearchSpec object
**User interaction**: None

Consolidates all constraints, assumptions, evidence needs, and validation requirements into a single specification that governs Steps 4–8.

Key decisions made here:
- `minimum_evidence_standard` is mechanically derived from risk_preference × time_horizon_preference.
- `disqualifying_failures` are defined with specific metrics and thresholds (not prose).
- `recommendation_requirements` are all hardcoded `true`: must return runner-up, must return rejections, must surface unknowns, must allow no valid candidate.

---

## Step 4: Candidate Generation

**Input**: ResearchSpec + DomainFrame
**Output**: 3–5 Candidate objects
**User interaction**: None

Generates multiple strategy directions. Distribution is enforced: minimum 1 baseline + 1 conservative + 1 exploratory. Candidates must be genuinely different — if >70% of architecture_outline components are shared between two candidates, diversity is insufficient.

Baseline is always the simplest known approach for the given archetype. It serves as the comparison reference in Steps 6–7.

Each candidate must articulate its own `core_assumptions` with `failure_impact` ("if this assumption is false, the candidate breaks because…") and `known_risks` (non-empty).

---

## Step 5: Evidence Planning + Data Acquisition

**Input**: ResearchSpec + Candidates
**Output**: EvidencePlan objects (per candidate) + acquired data + DataQualityReport objects
**User interaction**: None (except user data upload if needed)

This step has two phases:

**Phase A — Planning**: For each candidate, identify required evidence items, assess availability, flag biases, check point-in-time status, evaluate proxy options.

**Phase B — Acquisition**: Automatically acquire available public data (daily OHLCV via Yahoo Finance, FRED macro indicators, CFTC COT, index constituents). Run data quality checks (completeness, consistency, temporal, survivorship, point-in-time). Accept user-provided CSV/JSON for data not available via public APIs.

The output updates `coverage_metrics` with actual availability. `gap_severity` is computed: none (all required available), manageable (required obtainable or proxy exists), blocking (required unavailable, no proxy).

---

## Step 6: Validation Execution

**Input**: ValidationPlan objects + acquired data
**Output**: TestResult objects + ComparisonResult object
**User interaction**: None

Executes the validation plan against real data. v1 auto-executes:
- offline_backtest (daily data, max 20 years, max 500 instruments)
- out_of_sample (70/30 split)
- walk_forward (3-year training, 1-year step)
- regime_split (4 regimes: bull/bear/high_vol/low_vol)
- sensitivity (cost sensitivity, key parameter sensitivity)
- statistical tests (t-test, bootstrap, multiple testing correction)

Each test produces a TestResult with pass/fail per metric and statistical significance. Tests that map to disqualifying_failures generate immediate rejection signals.

ComparisonResult compares all candidates on the same metrics, with baseline as reference. Statistical significance of differences is computed.

---

## Step 7: Audit / Rejection

**Input**: Candidates + EvidencePlans + ValidationPlans + TestResults + ComparisonResult + ResearchSpec
**Output**: Audit objects (per candidate)
**User interaction**: None

Audits every candidate across 10 categories (assumption, evidence_gap, leakage_risk, overfitting_risk, realism, regime_dependency, complexity, observability, cost_assumption, recommendation_risk) using 48 issue patterns.

Runs in two modes:
- **Execution-informed**: When TestResults exist, severity is determined by actual data (e.g., out-of-sample Sharpe drop → overfitting severity adjustment).
- **Plan-based fallback**: When execution failed or data was unavailable, severity is estimated from plan-level information.

Compound patterns are checked: combinations of individually non-fatal issues that together are disqualifying (e.g., high Sharpe + leakage signals = "apparent good performance" pattern → disqualifying).

Any candidate with a disqualifying issue is rejected. Rejection reasons are recorded (min 3 sentences: what → why fatal → fixability).

If all candidates are rejected on first pass: return to Step 4 with rejection reasons as additional constraints. Generate new candidates. Re-run Steps 5–7. If all rejected again: proceed to Step 8 with best_candidate_id = null.

---

## Step 8: Recommendation

**Input**: Audit objects + Candidates + ComparisonResult
**Output**: Recommendation object
**User interaction**: None

Selects Primary (best) and Alternative (runner-up) from surviving candidates. They must differ in candidate_type.

`ranking_logic` must have ≥ 3 comparison axes with per-candidate assessment and verdict. "Overall judgment" without axis-level detail is prohibited (FC-03).

`confidence_label` is mechanically determined by FC-02 rules. v1 output is mostly `medium` or `low`. `high` requires: all required evidence available, zero critical issues, all disqualifying tests passed, complete validation plan — nearly unreachable at plan stage.

`open_unknowns` must be non-empty (zero unknowns is unrealistic). `critical_conditions` must be non-empty (unconditional recommendations don't exist). `recommendation_expiry` is mandatory (no perpetual recommendations).

---

## Step 9: Candidate Presentation

**Input**: Recommendation + Candidates + Audit + TestResults
**Output**: CandidateCard objects + PresentationContext
**User interaction**: Yes (user reviews 2 cards)

Compresses internal data into user-facing candidate cards. Each card has exactly 8 field groups: display_name, summary, expected return band, max loss estimate, confidence level, key risks, stop conditions headline, strategy approach.

The compression is intentional. The internal pipeline produces hundreds of data points per candidate. The card shows what's needed for an approval decision.

PresentationContext provides the 1-line validation summary, recommendation expiry, rejection headline, and caveats. This is the only exposure of the internal process — a single sentence proving that serious work happened.

Variations: 2 cards (normal), 1 card (only 1 survived), 0 cards (all rejected, with explanation and 3 alternative directions to try).

---

## Step 10: Approval Gate

**Input**: User's candidate selection + risk confirmation
**Output**: Approval object
**User interaction**: Yes (user confirms and approves)

The user selects one candidate and sees the approval screen: selected card re-displayed, key risks re-displayed, full stop condition list, re-evaluation schedule, Paper Run notice.

Approval requires:
- `risks_reviewed = true` (checkbox)
- `stop_conditions_reviewed = true` (checkbox)
- `paper_run_understood = true` (checkbox, v1)

No checkbox = button disabled. No shortcut. This is the ethical gate between validation and operation.

The Approval object records what was approved, under what conditions, with what safety mechanisms. It is the contract between the user and the system.

---

## Step 11: Paper Run Runtime

**Input**: Approval object + candidate strategy definition
**Output**: PaperRunState (continuously updated)
**User interaction**: Minimal (monthly report, status card)

The system operates the approved strategy autonomously:

**Daily cycle** (every trading day):
1. Acquire latest market data
2. Calculate signals using the approved strategy's logic
3. Update virtual portfolio (simulated trades at T+1 open)
4. Calculate performance metrics
5. Check all stop conditions
6. Run anomaly detection
7. Store results

**Stop condition monitoring**:
- Max drawdown -20% → halt_and_notify
- 3 consecutive months underperforming benchmark → halt_and_notify
- Signal anomaly (3σ deviation) → pause_and_notify
- Data quality failure (3 consecutive days) → pause_and_notify

**On halt**: Immediate stop. User notified within 1 hour. Resume requires re-approval (back to Step 10).

**Monthly report**: Auto-generated, pushed to user. 3–5 sentences + key numbers. No charts. No metrics the user needs to interpret.

**User-facing status card**: Single card showing status light (🟢🟡🔴⏸), current value, stop condition proximity, next report date, next re-evaluation date. Not a dashboard.

---

## Step 12: Re-evaluation

**Input**: PaperRunState + fresh market data
**Output**: ReEvaluationResult
**User interaction**: Only if outcome ≠ continue

**Quarterly re-evaluation**: Re-runs Steps 5–8 with the most recent data. Three outcomes:

| Outcome | System action | User action |
|---------|--------------|-------------|
| Continue | Automatic. Paper Run continues | None |
| Change candidate | Generates new CandidateCards. Presents to user | Re-approval required (Steps 9–10) |
| Stop all | Halts Paper Run | User can start new run |

**Triggered re-evaluation**: Also fires on stop_condition_hit, detected market_regime_change, or user_request. Same 3 outcomes.

Re-evaluation without re-approval is possible only for the "continue" outcome. Any change to what the user approved requires explicit re-approval.

---

## Loop invariants

1. All step outputs are JSON-serializable.
2. No candidate reaches Step 8 without passing through Step 7.
3. `confidence_label` is mechanically determined. No manual override.
4. Rejected candidates and their rejection reasons are retained, not discarded.
5. `open_unknowns` in Recommendation is never empty.
6. No candidate is presented to the user without stop conditions.
7. No Paper Run starts without explicit user approval.
8. No Paper Run resumes after halt without re-approval.
9. No candidate change is applied without re-approval.
10. All recommendations have an expiry.

---

**Role of this document**: This defines the sequence of operations from goal input to autonomous Paper Run. Every module in the system corresponds to one or more steps in this loop. Implementation must preserve the step ordering, the feedback loop on all-rejection, the approval gate, and the runtime lifecycle. If a module's behavior contradicts this loop definition, this document takes precedence.
