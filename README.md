# Give Me a DAY

Give Me a DAY is a validate-then-operate system for investment strategies.

Its mission is to transform AI intelligence into real-world outputs that actually work for humans.
Validation is the conversion layer between ideas and results, not an academic end in itself.

It internally researches, tests, compares, and rejects candidate directions, presents the 2 survivors to the user for approval, and upon approval operates the chosen strategy autonomously under predefined stop conditions.

## Architecture

![Give Me a DAY — Product Architecture](docs/assets/give-me-a-day-system-diagram-v2.png)

The system has three zones:

**User Input** — A single natural-language investment goal. No prompt engineering required.

**Internal Validation Engine** (hidden from user) — Domain Framing → Research Spec → Candidate Generation (3–5) → Evidence + Data Acquisition → Backtest + Statistical Testing → Audit / Rejection → Recommendation. The user does not see this process or its intermediate outputs.

**User Output + Runtime** — Exactly 2 candidates (Primary + Alternative) with expected return bands, estimated max loss, confidence level, and key risks. Approval is mandatory before any runtime begins. v1 runtime is Paper Run only (no real money). Guardrails include max drawdown, consecutive underperformance, signal anomaly, and data quality failure stop conditions. Monthly reports and quarterly re-evaluation with three outcomes: continue, change (requires re-approval), or stop.

## First wedge

- Investment research
- Strategy validation
- Hypothesis-testing pipelines

## What it does

- Receives a natural-language investment goal
- Internally researches, tests, compares, and rejects candidate strategies
- Presents 2 surviving candidates with return expectations, risks, and confidence
- Requires explicit approval before operation
- Operates via Paper Run (simulated, no real money in v1)
- Monitors stop conditions and halts automatically when breached
- Re-evaluates quarterly with fresh data

## What it is not

- A generic workflow automation tool
- A broad “build anything with AI” product
- A prompt helper or code generator
- A robo-advisor that skips validation
- A dashboard where users analyze backtests themselves

## Product truth

**Give Me a DAY does not mainly generate code.
It generates validated direction that can be operated in reality.**

In v1, investment is the first high-signal domain pack.
All recommendations are conditional. All recommendations expire. No guaranteed outcomes.
The longer-term product identity is broader: a validation engine that gets better over time at producing successful real-world outputs as outcomes accumulate.

## Source of truth

1. `CLAUDE.md` — Project identity and non-negotiables
2. `docs/product/product_definition.md` — What the product is and does
3. `docs/product/v1_boundary.md` — What is in/out of scope for v1
4. `docs/system/core_loop.md` — 12-step validate-then-operate pipeline
5. `docs/system/internal_schema.md` — All data structures
6. `docs/system/execution_layer.md` — Data acquisition, backtests, Paper Run
7. `docs/output/v1_output_spec.md` — User-facing outputs and runtime
8. `docs/assets/give-me-a-day-system-diagram-v2.png` — Canonical architecture diagram
