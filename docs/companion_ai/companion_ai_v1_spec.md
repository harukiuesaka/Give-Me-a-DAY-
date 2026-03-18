# Companion AI v1 Specification

**Status**: Design-complete. Not yet implemented.
**Last updated**: 2026-03-18
**Scope**: v1 only — Goal Intake and Approval Gate

---

## 1. Objective

Define a minimal, product-correct Companion AI layer that helps users navigate the
two points where human judgment is required: **Goal Intake** (Step 1) and **Approval Gate**
(Step 10).

The Companion AI is not a chatbot. It is not a prompt engineer. It is a structured
clarification layer that converts everyday language into validated inputs the pipeline
can act on, and converts technical system contracts into plain-language that a
non-expert user can genuinely understand before committing.

---

## 2. Why It Matters

The current pipeline has two failure modes that sit outside the internal engine:

**At Goal Intake:**
Users submit ambiguous or incomplete goals. When a goal lacks success criteria, risk
preference, or time horizon, the system silently assigns defaults. Those defaults shape
the entire downstream pipeline — archetype classification, evidence standard,
validation thresholds, candidate generation. A wrong default compounds through all
12 steps. The user never sees it.

**At Approval Gate:**
The current approval is three checkboxes. The user must confirm they have reviewed:
risks, stop conditions, and Paper Run status. But nothing verifies that the user
actually understood any of it. A user can check all three boxes in 10 seconds without
reading anything. The approval gate is an ethical contract. A checkbox does not make
it one.

The Companion AI addresses both failure modes without adding friction for users who
already know what they want.

---

## 3. Scope Boundaries

### In scope (v1)

- Clarification questions at Goal Intake when the goal is incomplete or ambiguous
- Inference of structured constraints (`risk_preference`, `time_horizon_preference`,
  `success_definition`, `must_not_do`) from everyday language answers
- Contradiction surfacing at Goal Intake
- Plain-language explanation of candidate risk and stop conditions at Approval Gate
- Surfacing what the user is actually committing to before they approve
- Proactive flag if a user's answer contradicts their stated goal

### Out of scope (v1)

- Free-form multi-turn conversation about investment strategy
- Coaching users on how to structure goals (that is prompt engineering, not product value)
- Modifying the internal pipeline output based on companion conversation
- Companion involvement in Steps 2–9 (pipeline is entirely internal)
- Companion involvement in Paper Run status or re-evaluation
- Companion as a general assistant or question-answering interface
- Changing any stop condition thresholds based on user conversation
- Personalizing the internal logic based on companion interaction
- Companion memory across sessions (v1 is stateless per run)

---

## 4. Companion Role at Goal Intake (Step 1)

### 4.1 Trigger condition

The Companion activates when any of the following are true after initial goal submission:

| Trigger | Condition |
|---------|-----------|
| Goal is vague | `raw_goal` length < 40 characters, or no measurable outcome detectable |
| Success criteria missing | `success_criteria` field empty, and goal text contains no quantifiable target |
| Risk preference unclear | `risk` field empty, and no risk signal in goal text |
| Time horizon unclear | `time_horizon` field empty, and no horizon signal in goal text |
| Contradiction detected | Goal text signals conflict (e.g., "high return" + "zero risk") |
| Out-of-scope signal | Goal text contains out-of-scope signals (crypto, FX leverage, options, etc.) |

If none of these triggers fire — goal is clear, all fields are either provided or
inferable with high confidence — the Companion is silent. No questions are asked.
The pipeline proceeds directly.

### 4.2 Question set

The Companion asks only what is necessary to resolve the above triggers.
Maximum questions per session: **4**. If more than 4 are needed, the remaining
gaps go into `open_uncertainties` and the pipeline proceeds with defaults.

**Q1 — Success clarification** (if success trigger fires):

> "What would make this worthwhile for you — roughly what kind of return, or over what
> period? Even a rough answer helps. For example: 'double my money in 5 years' or
> 'beat the stock market index over 3 years'."

**Q2 — Risk clarification** (if risk trigger fires):

> "How much are you comfortable losing before you'd want the system to stop?
> For example: 'I'd want it to stop if I lose 5% of what I started with' or
> 'I can tolerate losing 30% if the upside is high enough'."

**Q3 — Time horizon clarification** (if time horizon trigger fires):

> "How long should the system run before you'd want to evaluate whether it's working?
> For example: 'I want to see results in 3 months' or 'I'm thinking about a 5-year view'."

**Q4 — Exclusion clarification** (if out-of-scope signal fires):

> "I noticed your goal mentions [X]. That's currently outside what the system can validate.
> Would you like to focus on [closest in-scope alternative], or would you prefer to
> start with a different goal?"

Contradiction questions are handled inline as warnings, not as separate questions
(see §4.4).

### 4.3 Constraint inference rules

The following rules map everyday answers to structured constraints. These are applied
mechanically, not through LLM judgment in v1 (v1 uses pattern matching and
keyword extraction; LLM-based inference is a v2 enhancement):

**Risk preference mapping:**

| User answer signal | Inferred `risk_preference` |
|-------------------|---------------------------|
| "don't want to lose", "preserve capital", "safe", "loss within 5%" | `very_low` |
| "small loss is okay", "lose up to 10-15%", "conservative" | `low` |
| "can handle ups and downs", "lose up to 25-30%", "some risk is fine" | `medium` |
| "willing to lose a lot for big upside", "aggressive", "lose 40%+ is okay" | `high` |
| No clear signal | Default: `medium`, added to `open_uncertainties` |

**Time horizon mapping:**

| User answer signal | Inferred `time_horizon_preference` |
|-------------------|-----------------------------------|
| "days", "this week", "next few days" | `fast` |
| "1 month", "30 days", "short term" | `one_month` |
| "1 week", "few weeks" | `one_week` |
| "1 year", "long term", "several years", "5 years" | `quality_over_speed` |
| No clear signal | Default: `one_week`, added to `open_uncertainties` |

**Success definition extraction:**

If the user provides a numerical target (e.g., "beat the index", "10% per year",
"double in 5 years"), that text becomes the `success_definition` verbatim (truncated
to 200 chars). If the answer is qualitative only, the Companion maps it to the
appropriate default from `_default_success_definition()` in `goal_intake.py` and
records the mapping in `open_uncertainties`.

**Must-not-do extraction:**

Any answer mentioning explicit exclusions ("not crypto", "not leverage", "no
short-selling") is parsed and appended to `must_not_do`. The current keyword-based
exclusion parsing in `goal_intake.py` is sufficient for v1.

### 4.4 Contradiction surfacing

If the Companion detects a contradiction between stated preferences, it surfaces it
inline — before asking for clarification or proceeding:

> **Heads up**: Your goal mentions [high returns], but you've indicated [very low risk
> tolerance]. These are in tension. Most high-return strategies carry meaningful
> drawdown risk. The system will find the best available option within your constraints,
> but it may reject high-return candidates if they conflict with your stated risk limits.
> This is intentional. Do you want to adjust either preference, or proceed?

Contradiction is not a blocker. The user can proceed with the contradiction visible
in `open_uncertainties`. The pipeline's audit logic (Step 7) already handles
risk/return tradeoff realism — the contradiction flag just makes it legible to the
user upfront rather than buried in an audit finding.

Contradiction triggers:
- `risk_preference = very_low` AND any return target > 8% annually
- `risk_preference = very_low` AND `must_not_do` is empty (no exclusions suggests
  user hasn't thought through constraints)
- `time_horizon_preference = fast` AND any mention of "long-term" or "stable income"
- `must_not_do` contains an asset class that was mentioned positively in `raw_goal`

### 4.5 Output

The Companion produces a **refined `UserIntent` object** — same schema as §1 of
`internal_schema.md`, same Pydantic class. No new schema objects are required.

What changes:
- `open_uncertainties` is populated with explicit notes on what was inferred, defaulted,
  or flagged as a contradiction
- `success_definition` reflects the Companion-clarified version
- `risk_preference` and `time_horizon_preference` reflect inferred values (not silent defaults)

A `companion_context` block is added to the `UserIntent` for traceability:

```jsonc
"companion_context": {
  "questions_asked": ["Q1", "Q2"],
  "inferences_made": [
    { "field": "risk_preference", "from": "don't want to lose much", "inferred": "very_low" }
  ],
  "contradictions_flagged": [
    "high return target (12%+) vs. very_low risk preference"
  ],
  "companion_active": true
}
```

This block is stored with the UserIntent but is not surfaced in the UI after intake.
It is available for audit tracing and debugging. It does not affect pipeline logic.

---

## 5. Companion Role at Approval Gate (Step 10)

### 5.1 Current state and problem

The current Approval Gate requires three checkboxes:
- `risks_reviewed` — "I have reviewed the key risks"
- `stop_conditions_reviewed` — "I have reviewed the stop conditions"
- `paper_run_understood` — "I understand this is a Paper Run (simulated)"

The current UI displays the candidate card and a list of stop conditions in their
technical form (e.g., "SC-01: max drawdown threshold: -20%"). A user who has never
managed a portfolio does not know what a drawdown is, what -20% means in emotional
and financial terms, or what happens to the Paper Run when SC-01 triggers.

The checkboxes are not a substitute for comprehension.

### 5.2 Companion role

The Companion at Approval Gate is **not conversational**. It is a **plain-language
translation layer** that:

1. Translates each stop condition into plain English before the checkbox
2. Translates the candidate's key risks into plain English
3. Explains what "Paper Run" means concretely
4. Asks one optional confirmation question to verify comprehension
5. Flags if answers suggest the user has misunderstood something material

The companion does **not** change the approval flow. The three checkboxes remain.
Approval is still blocked unless all three are checked. The companion adds
understanding without removing the gate.

### 5.3 Stop condition translation

Before the `stop_conditions_reviewed` checkbox, the Companion renders each stop
condition in plain language:

**SC-01** (displayed as):
> **Automatic stop: if the portfolio falls 20% from its starting value.**
> Example: if you approved a ¥1,000,000 Paper Run and it fell to ¥800,000, the system
> stops automatically and notifies you. You would need to review and re-approve to
> continue.

**SC-02** (displayed as):
> **Automatic stop: if the strategy underperforms the market index for 3 months in a row.**
> This triggers even if the strategy isn't losing money — it means the strategy isn't
> keeping up with a simple market benchmark.

**SC-03** (displayed as):
> **Automatic pause: if the strategy generates an unusual signal (more than 3 standard
> deviations from normal behavior).**
> The system pauses and notifies you rather than acting on a potentially erroneous signal.

**SC-04** (displayed as):
> **Automatic pause: if data quality problems persist for 3 trading days in a row.**
> The system won't continue operating on data it can't trust.

The technical identifiers (SC-01 through SC-04) are preserved in the UI alongside
the plain-language translation. They are not hidden.

### 5.4 Risk translation

Before the `risks_reviewed` checkbox, the Companion translates each `key_risk` from
the CandidateCard:

CandidateCard key risks are short, technically-framed strings (e.g.,
"Momentum factor crowding in regime shift"). For each, the Companion adds a
plain-language annotation:

> **"Momentum factor crowding in regime shift"**
> In plain terms: when too many strategies follow the same momentum signals, they can
> all exit at once. This can cause large, fast losses during market turning points.
> This is a known risk of this type of strategy.

The annotation is generated at presentation time, not stored in the pipeline objects.
In v1, annotations use a small set of templates keyed to risk category patterns
(crowding, regime change, data leakage, cost underestimation, overfitting, liquidity).
LLM-generated annotations are a v2 enhancement.

### 5.5 Paper Run explanation

Before the `paper_run_understood` checkbox, the Companion renders:

> **What "Paper Run" means:**
> The system will simulate running this strategy every trading day using real market
> data — but with virtual money only. No real money is involved. No trades are placed.
> The purpose is to observe whether the strategy behaves the way the backtest predicted
> in live market conditions.
>
> Paper Run results are not a guarantee that real execution would produce the same
> outcomes. They are a check that the strategy logic works in real-time conditions,
> not just historical ones.

This text is fixed in v1. It does not vary by candidate.

### 5.6 Comprehension check (optional)

After all three translations are displayed and before the checkboxes are enabled,
the Companion asks a single yes/no comprehension check:

> **Quick check**: If the Paper Run portfolio fell from ¥1,000,000 to ¥800,000,
> what would happen?
>
> ○ The system would stop automatically and notify me
> ○ Nothing — I'd need to check manually
> ○ The system would try to recover the loss automatically

If the user selects the correct answer, the checkboxes are enabled immediately.
If the user selects an incorrect answer, the Companion shows:

> That's not quite right. Based on SC-01, if the portfolio falls 20%, the system stops
> automatically and notifies you. You would then decide whether to re-approve and continue.
> Please re-read the stop conditions above before checking the box.

The checkboxes remain disabled until the correct answer is selected.

This is the only question at Approval Gate. It is not skippable in v1.
The question is seeded from SC-01 (drawdown) because that is the most common
trigger and the most concrete to reason about.

### 5.7 Output

The Companion does not modify the `Approval` object schema. The output is still the
same `Approval` Pydantic object.

A `companion_context` block is added to the Approval for tracing:

```jsonc
"companion_context": {
  "translations_rendered": ["SC-01", "SC-02", "SC-03", "SC-04", "key_risks", "paper_run"],
  "comprehension_check_passed": true,
  "comprehension_check_attempts": 1
}
```

This block is stored with the Approval record but does not affect pipeline logic.

---

## 6. Architecture Fit

### 6.1 What exists today

- `backend/src/pipeline/goal_intake.py` — `process_goal_intake()` takes a
  `CreateRunRequest` and returns a `UserIntent`. It does keyword classification,
  default assignment, and uncertainty recording. No LLM, no conversation.
- `backend/src/api/routes.py` — `POST /api/v1/runs` fires the pipeline in a background
  thread immediately after `CreateRunRequest` is received. No clarification round-trip.
- `backend/src/pipeline/approval_controller.py` — validates confirmations and creates
  `Approval` object. No comprehension check.
- `frontend/src/pages/ApprovalPage.tsx` — renders candidate card + three checkboxes.
  No translations.

### 6.2 What must change

**Backend — Goal Intake clarification endpoint:**

New endpoint: `POST /api/v1/runs/preflight`

Takes `CreateRunRequest`, runs the Companion trigger evaluation (§4.1), and returns
a `CompanionGoalResponse`:

```jsonc
{
  "needs_clarification": true,
  "questions": [
    { "id": "Q1", "text": "...", "type": "free_text" }
  ],
  "contradictions": ["..."],
  "inferences": [
    { "field": "risk_preference", "from": "...", "inferred": "..." }
  ]
}
```

If `needs_clarification: false`, the frontend proceeds directly to `POST /api/v1/runs`.

New endpoint: `POST /api/v1/runs/preflight/submit`

Takes `CreateRunRequest` + `CompanionAnswers`, applies inference rules (§4.3),
produces refined `CreateRunRequest`, fires `POST /api/v1/runs` internally.

**Backend — Approval translation endpoint:**

New endpoint: `GET /api/v1/runs/{run_id}/approval-context`

Returns:
```jsonc
{
  "stop_condition_translations": [
    { "id": "SC-01", "plain_language": "..." },
    ...
  ],
  "risk_translations": [
    { "risk": "Momentum factor crowding in regime shift", "annotation": "..." }
  ],
  "paper_run_explanation": "...",
  "comprehension_check": {
    "question": "...",
    "options": [...],
    "correct_index": 0
  }
}
```

This endpoint is read-only. It does not modify any pipeline state.

**Frontend changes:**

- `InputPage.tsx`: Add preflight call. If `needs_clarification: true`, show
  Companion question set before submitting. If `false`, submit directly.
- `ApprovalPage.tsx`: Fetch `approval-context` before rendering checkboxes.
  Render translations above each checkbox. Show comprehension check before enabling
  checkboxes.

### 6.3 What does not change

- `UserIntent` schema: same Pydantic object, with `companion_context` as an optional
  additional field (no pipeline logic reads it)
- `Approval` schema: same Pydantic object, with `companion_context` as an optional
  additional field
- Pipeline steps 2–9: unchanged. Companion does not touch the internal engine.
- All 144 existing tests: no modifications required
- v1 boundary: no new data sources, no new domains, no new pipeline steps
- Stop condition thresholds: unchanged. Companion explains them, does not modify them.
- Approval gate: still requires all three checkboxes. Not bypassable.

### 6.4 New schema objects

Minimal additions, none touching the pipeline:

```python
class CompanionQuestion(BaseModel):
    id: str              # "Q1" through "Q4"
    text: str
    type: str            # "free_text" | "multiple_choice" | "yes_no"
    options: list[str] = Field(default_factory=list)

class CompanionGoalResponse(BaseModel):
    needs_clarification: bool
    questions: list[CompanionQuestion]
    contradictions: list[str]
    inferences: list[dict]   # {field, from, inferred}

class CompanionAnswers(BaseModel):
    answers: dict[str, str]   # question_id -> answer text

class CompanionContext(BaseModel):
    # Attached to UserIntent and Approval as optional field
    questions_asked: list[str]
    inferences_made: list[dict]
    contradictions_flagged: list[str]
    comprehension_check_passed: bool = False
    comprehension_check_attempts: int = 0
    companion_active: bool = True
```

These objects live in a new module: `backend/src/companion/`.

---

## 7. Key Design Decisions

### Decision 1: Companion is optional, not mandatory

If the user provides a complete, clear goal, the Companion does not activate. No
questions are asked. The `POST /api/v1/runs` endpoint continues to exist and work
without a preflight call. The Companion is a support layer, not a gating dependency.

### Decision 2: Maximum 4 questions at Goal Intake

More than 4 questions shifts the experience from "clarification" to "interrogation."
The value of Give Me a DAY is that the user provides minimal input and the system does
the work. Four questions is the outer limit. Remaining gaps go into `open_uncertainties`.

### Decision 3: One comprehension check at Approval Gate, not many

Multiple comprehension checks add friction without proportional benefit. SC-01
(drawdown) is the most concrete and most frequently triggered condition. It is the
right single test. Passing it implies awareness of automatic halt behavior, which is
the most important property of the approval contract.

### Decision 4: Translations are pre-written templates, not LLM-generated in v1

LLM-generated translations introduce latency, unpredictability, and the risk of
confusing or incorrect plain language. The stop conditions are fixed (SC-01 to SC-04).
Their translations are also fixed and pre-written. Risk annotations use a small
keyword-keyed template set. LLM-based dynamic annotation is a v2 enhancement.

### Decision 5: `companion_context` does not affect pipeline logic

Companion outputs are traceable but not load-bearing. The pipeline does not branch
on `companion_context` fields. This keeps the companion as a support layer and
prevents it from introducing subtle logic dependencies.

---

## 8. Risks and Failure Modes

| Risk | Description | Mitigation |
|------|-------------|------------|
| Companion over-activates | Asks questions when the goal is clear enough | Tight trigger conditions (§4.1). If not triggered, companion is silent |
| Inference is wrong | Maps "I can handle some loss" → `very_low` when user meant `medium` | Inference result shown to user before pipeline start. User can correct before proceeding |
| Comprehension check feels patronizing | Experienced users resent being quizzed | Check is one question, fast. Framed as a "quick check" not a test. Passing is easy for anyone who read the translations |
| Translations are imprecise | Plain-language loses technical accuracy | Technical identifiers preserved alongside translations. Translations are checked against stop condition logic during spec review |
| Companion adds latency | Preflight round-trip delays pipeline start | Preflight is fast (no LLM, pattern matching only). If `needs_clarification: false`, there is no latency at all |
| Frontend complexity | Two new API calls for Goal Intake, one for Approval | Calls are lightweight. No blocking dependencies. Preflight result can be cached for session |

---

## 9. Explicitly Out of Scope

- Companion involvement in any pipeline step other than Goal Intake and Approval Gate
- Conversation history or memory across runs
- Companion-driven modification of internal pipeline parameters
- User ability to "negotiate" stop condition thresholds via companion
- LLM-based inference (v1 uses pattern matching only)
- Companion as a general investment advisor or assistant
- Any expansion of v1 domain scope triggered by companion interaction
- Companion explaining the internal pipeline (it is intentionally opaque to the user)

---

## 10. Recommended Next Action

This spec is ready for implementation review. Before implementation begins:

1. Confirm acceptance of the 4-question limit and comprehension-check model
2. Confirm the `companion_context` as an optional, non-load-bearing addition to
   `UserIntent` and `Approval`
3. Confirm `docs/companion_ai/` as the correct spec location (not inside `docs/system/`)
4. Confirm that v1 uses template-based inference (not LLM), and LLM-based inference
   is explicitly deferred to v2
5. Define which question templates and risk annotation templates to write in the
   implementation task

Once confirmed, implementation should proceed in the following order:
1. New `backend/src/companion/` module (trigger evaluation, inference rules, templates)
2. Two new API endpoints (`/preflight`, `/preflight/submit`, `/approval-context`)
3. Domain model additions (`CompanionQuestion`, `CompanionGoalResponse`, `CompanionAnswers`, `CompanionContext`)
4. Frontend integration (`InputPage.tsx`, `ApprovalPage.tsx`)
5. Tests for companion module and endpoints

---

**Role of this document**: This is the authoritative v1 spec for the Companion AI
layer. It defines scope, behavior, architecture fit, and constraints. Implementation
must not exceed this spec without explicit re-scoping. This document does not supersede
any existing source-of-truth documents — it extends them for the companion layer only.
