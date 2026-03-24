# LLM Quality Evaluation — Give Me a DAY

**Version**: 1.0
**Created**: 2026-03-24
**Status**: Operational (not yet run on live outputs)
**OL-017 ref**: This document makes OL-017 measurable and testable.

---

## 1. What Is Being Evaluated

The LLM powers three pipeline modules that generate research-critical output. These are the only modules where LLM failure has direct impact on product value. Failure elsewhere falls back gracefully.

### Module 2: DomainFramer (`backend/src/pipeline/domain_framer.py`)

**What it generates**: A `DomainFrame` struct containing:
- `archetype`: one of 8 strategy archetypes (FACTOR, STAT_ARB, EVENT, MACRO, ML_SIGNAL, ALT_DATA, HYBRID, UNCLASSIFIED)
- `reframed_problem`: the user's goal rephrased as a testable research problem
- `core_hypothesis`: a single-sentence hypothesis
- `testable_claims`: 3+ claims, one per layer (premise / core / practical), each with a falsification condition
- `critical_assumptions`: 2+ assumptions
- `regime_dependencies`: 2+ market regime dependencies
- `comparable_known_approaches`: 1+ known approaches

**Why it matters**: This output drives everything downstream. A bad archetype propagates wrong candidates. A weak `core_hypothesis` produces untestable plans. A missing `falsification_condition` makes the validation plan unfalsifiable. This is the highest-risk LLM call in the product.

**Failure modes ranked by severity**:
1. `falsification_condition` is empty, circular, or unmeasurable → validation becomes theater
2. `archetype` is wrong for the given goal → all candidates point the wrong direction
3. `testable_claims` are too vague to operationalize → no working test plan possible
4. `reframed_problem` is a paraphrase of the raw goal, not a research problem → no added value
5. `comparable_known_approaches` are fabricated or irrelevant → misleads user

---

### Module 4: CandidateGenerator (`backend/src/pipeline/candidate_generator.py`)

**What it generates**: 3–5 `Candidate` structs, typed as baseline / conservative / exploratory, each with:
- `summary`: 2-sentence description
- `architecture_outline`: step-by-step sketch
- `core_assumptions`: 1+ assumptions with `failure_impact`
- `known_risks`: 2+ risks
- `validation_burden` and `implementation_complexity`: low / medium / high

**Why it matters**: The candidates are the core product deliverable. Candidates that are too similar to each other remove the value of comparison. Candidates that violate the user's constraints are useless. Candidates without real `known_risks` produce false confidence.

**Failure modes ranked by severity**:
1. All 3 candidates are nearly identical (no real diversity) → comparison produces no signal
2. Candidate violates `must_not_do` constraint → product is dangerous
3. `known_risks` is generic boilerplate → no actionable risk signal
4. `core_assumptions.failure_impact` is empty or circular → assumptions not operative
5. `validation_burden` is systematically underestimated → user under-plans testing effort

---

### Module 6: ValidationPlanner (`backend/src/pipeline/validation_planner.py`)

**What it generates**: `ValidationPlan` with 4+ tests (offline_backtest, out_of_sample, walk_forward, regime_split), each with `failure_conditions`.

**Why it matters**: A validation plan with weak `failure_conditions` is not a plan — it is a guarantee of success. This is the product's core claim: "rejection is a feature." If the validation plan cannot reject anything, the product is not doing its job.

**Failure modes ranked by severity**:
1. `failure_conditions` are absent, vague, or not measurable → plan is unfalsifiable
2. Required tests (offline_backtest, out_of_sample, walk_forward, regime_split) are missing → plan is incomplete
3. `failure_conditions` are trivially easy to pass (e.g., "return > -100%") → plan produces false confidence
4. `method_summary` is too vague to implement → plan is unusable

---

## 2. Definition of "Usable"

**DomainFramer output is usable if all of the following hold**:
- `archetype` is not UNCLASSIFIED for any goal where the strategy type is clearly identifiable
- `reframed_problem` is distinct from the raw_goal (adds problem-framing value)
- Every `testable_claim` has a `falsification_condition` that is non-circular and operationalizable
- `regime_dependencies` contains ≥ 2 distinct items
- `comparable_known_approaches` contains ≥ 1 real (non-fabricated) approach with a real outcome

**CandidateGenerator output is usable if all of the following hold**:
- All 3 required types are present (baseline, conservative, exploratory)
- Type diversity is real: candidates differ in architecture, not just name
- No candidate violates the `must_not_do` constraints from the user input
- `known_risks` per candidate contains ≥ 2 distinct, non-generic risks
- `core_assumptions` per candidate contains ≥ 1 with a non-empty, non-circular `failure_impact`

**ValidationPlanner output is usable if all of the following hold**:
- All 4 required test types are present
- Each test has ≥ 1 `failure_condition` that is measurable (contains a numeric threshold or concrete falsifiable criterion)
- No `failure_condition` is trivially trivial (e.g., "loss > 100%", "return is not NaN")

---

## 3. Evaluation Rubric

### Dimensions (applied per module output)

Each dimension is scored 1–5. Scores ≤ 2 on any dimension = **Not Ready**. Average ≥ 4.0 = **Acceptable for limited testing**.

---

#### D1 — Structural Compliance (pass/fail gating)
Does the output match the required JSON schema and field constraints?

| Score | Criterion |
|-------|-----------|
| 5 | All required fields present, types correct, minimums met |
| 3 | 1–2 optional fields missing; required fields all present |
| 1 | Any required field absent or wrong type → auto-fail |

**Failure examples**: missing `falsification_condition`, `candidates` list has < 3 items, `failure_conditions` is empty array.

---

#### D2 — Instruction Adherence
Does the output follow the prompt's explicit rules?

| Score | Criterion |
|-------|-----------|
| 5 | All rules followed (archetype from valid set, minimum counts met, forbidden checks applied) |
| 3 | 1 rule violated (e.g., only 1 regime_dependency instead of 2) |
| 1 | ≥ 2 rules violated, or a hard rule violated (forbidden behavior in candidate) |

---

#### D3 — Falsifiability
Are claims, assumptions, and failure conditions actually testable?

| Score | Criterion |
|-------|-----------|
| 5 | Each claim/condition contains a measurable threshold or observable event |
| 4 | Most conditions measurable; 1–2 are vague but operationalizable |
| 3 | Some conditions are vague; require interpretation |
| 2 | Conditions are present but circular ("fails if it doesn't work") |
| 1 | Conditions absent or trivially unfalsifiable |

**Failure examples**: `falsification_condition: "戦略が機能しない場合"`, `failure_conditions: ["パフォーマンスが悪い"]`

---

#### D4 — Relevance to Input
Does the output address the actual user goal, not a generic proxy?

| Score | Criterion |
|-------|-----------|
| 5 | Output directly addresses specific goal details (asset class, market, constraints) |
| 4 | Output is relevant but under-specific (ignores some constraints) |
| 3 | Output is generically applicable to many goals; not tuned to this one |
| 2 | Output ignores key constraints from the input |
| 1 | Output is wrong for the input (wrong archetype, wrong market, violates constraints) |

---

#### D5 — Candidate Diversity (CandidateGenerator only)
Are the 3 candidate strategies genuinely different approaches?

| Score | Criterion |
|-------|-----------|
| 5 | Fundamentally different architectures, data requirements, risk profiles |
| 4 | Clear differences in approach, minor overlaps |
| 3 | 2 of 3 candidates are similar variants of the same idea |
| 2 | All 3 are slight variations of the same approach |
| 1 | Candidates are essentially identical |

---

#### D6 — Non-Hallucination
Are all referenced facts, approaches, and methods real and accurate?

| Score | Criterion |
|-------|-----------|
| 5 | All references verifiable; no fabricated strategies, datasets, or outcomes |
| 4 | 1 minor inaccuracy (easily correctable) |
| 3 | 1–2 plausible but unverifiable claims |
| 2 | 1 clearly wrong or fabricated claim |
| 1 | Multiple fabrications; references invented outcomes |

**Failure examples**: `comparable_known_approaches` with a named strategy that does not exist, cited Sharpe ratios that are fabricated.

---

### Scoring Summary

| Module | Applicable Dimensions |
|--------|-----------------------|
| DomainFramer | D1, D2, D3, D4, D6 |
| CandidateGenerator | D1, D2, D4, D5, D6 |
| ValidationPlanner | D1, D2, D3 |

**Not Ready threshold**: Any dimension score ≤ 2, OR D1 = fail.
**Acceptable for limited testing**: All dimensions ≥ 3, average ≥ 4.0.
**Ready for user exposure**: All dimensions ≥ 4, average ≥ 4.5.

---

## 4. Evaluation Procedure

### Setup

- Model under test: `claude-sonnet-4-20250514` (Observed: `backend/src/llm/client.py`)
- Temperature: 0.3 (deterministic-leaning, but not fully deterministic)
- Source: `backend/src/llm/prompts.py` — all prompts used as-is, no modification
- Fallback state: API key set; `LLMClient.available == True`

### How to run

**Manual procedure (v1 — pre-automation)**

1. For each test case in `evals/llm_quality_cases.json`:
   - Extract `module`, `input`, `scenario_label`
   - Construct the prompt using the corresponding template in `backend/src/llm/prompts.py`
   - Call the API once (single run; do not cherry-pick)
   - Record raw output in `evals/results/run_YYYY-MM-DD.jsonl` (one JSON object per case)

2. Score each output on applicable dimensions using the rubric above.
   Record scores in `evals/results/scores_YYYY-MM-DD.csv`.

3. Flag any case where D1 = fail or any dimension ≤ 2.

4. Aggregate: compute per-case average, per-module average, overall average.

### Thresholds for action

| Result | Action |
|--------|--------|
| Any D1 = fail | Stop. Fix structural schema issue before any testing proceeds. |
| Any dimension ≤ 2 | File a specific issue against the relevant prompt in `backend/src/llm/prompts.py`. |
| Module average 2.5–3.5 | Prompt is functional but unreliable. Acceptable for internal testing only. |
| Module average ≥ 4.0 | Acceptable for limited external testing. Document conditions. |
| Module average ≥ 4.5 | Ready for user exposure with monitoring. |

### Record format

Each eval run produces:
- `evals/results/run_YYYY-MM-DD.jsonl` — raw LLM outputs (one JSON line per case)
- `evals/results/scores_YYYY-MM-DD.csv` — scores per case per dimension
- Update `docs/state/engineering.md` with: run date, module average scores, evidence label = Observed

### First run expectation

The first run will establish baseline scores. Do not expect "Acceptable" on the first run. Expect to find at least one dimension ≤ 3 per module. The goal of the first run is to locate the worst failure modes, not to validate quality.

---

## 5. What This Eval Does Not Cover

- Runtime performance or latency (not a v1 concern)
- Multi-turn consistency (pipeline is single-pass)
- Full end-to-end pipeline with real user sessions
- Financial accuracy of generated strategies (requires domain expert review)
- Comparison between prompt versions (requires baseline first)

These are out of scope until baseline exists.
