# CLAUDE.md

## Project Identity

You are working on **Give Me a DAY**.

Give Me a DAY is **not** a generic AI workflow automation tool.
It is **not** a broad “build anything with AI” product.
It is **not** a prompt improvement layer.
It is **not** a polished code generator pretending to be a product strategy engine.

Give Me a DAY is a **validation-first product for advanced systems**.

Its first wedge is:

- investment research
- strategy validation
- hypothesis-testing pipelines

Its core value is not code generation.
Its core value is:

- defining what must be tested
- specifying what evidence is required
- planning or structuring research loops
- generating multiple candidate system directions
- comparing them honestly
- rejecting weak approaches
- returning a conditionally recommended direction

The product does **not** mainly win by translating vague desires into structured requirements.
That is useful, but not the center.

The center is:
**comparison, validation, rejection, and conditional recommendation for high-complexity systems.**

Investment is the v1 proving ground, not the terminal identity.
The deeper product thesis is to convert AI intelligence into real-world successful outcomes, then improve future outcomes by learning from validation and runtime feedback.

---

## Core Truth

Give Me a DAY does not generate pretty code.

**It generates validated direction.**

The hardest part of advanced system building is usually not writing code.
The hardest part is:

- defining what must actually be tested
- finding or specifying the right data
- identifying weak assumptions
- comparing alternative system directions honestly
- rejecting attractive but fragile options
- knowing what is still unknown
- avoiding false confidence

This repo exists to build a product that owns that missing middle.

---

## First Wedge

The current source of truth is that v1 is centered on:

**investment research / strategy validation / hypothesis-testing systems**

This means:
- research-heavy
- validation-heavy
- comparison-heavy
- rejection-heavy
- evidence-dependent

It does **not** mean:
- generic office automation
- CRM helper tools
- ordinary productivity workflows
- “AI can save time” product abstractions
- broad workflow-builder positioning

If a proposal drifts in that direction, push back.

---

## Product Non-Negotiables

1. **No recommendation without critique**  
   Any serious recommendation must be preceded by comparison and critique.

2. **No candidate without assumptions**  
   Every candidate system direction must expose its assumptions.

3. **No validation plan without failure conditions**  
   A plan that cannot fail is not a plan.

4. **No “best” language without conditions**  
   “Best” always means “best under current assumptions, evidence, and constraints.”

5. **Unknowns must remain visible**  
   Never hide unresolved uncertainty for the sake of sounding decisive.

6. **Rejection is a feature**  
   A major part of product value is telling the user which attractive directions should be rejected.

7. **UI simplicity must not weaken internal rigor**  
   The user-facing flow should be simple, but the internal logic should behave like a research committee, not a toy chatbot.

8. **Do not drift into generic workflow automation**  
   Even if it sounds commercially broader, it weakens the wedge.

9. **Do not collapse into code generation**  
   Code may be an output artifact, but it is not the product center.

10. **v1 must stay narrow**  
    Broadness is not a sign of strength. Narrowness with real depth is.

---

## In-Scope for v1

The current v1 scope is centered on:

- user goal intake for advanced system-building intent
- domain framing for validation-heavy problems
- research spec compilation
- evidence and data requirement planning
- candidate system generation
- validation plan generation
- audit / rejection logic
- recommendation package generation
- explicit assumptions, conditions, and next validation steps

The expected output is **not** just a plan or code scaffold.

The expected output is a **recommendation package** that includes:

- user goal summary
- research framing
- candidate set
- evidence requirements
- validation plan
- audit findings
- rejected options
- best current candidate
- runner-up
- conditions under which the recommendation may change
- next validation steps

---

## Explicitly Out of Scope for v1

Unless explicitly re-scoped, do **not** optimize for or introduce:

- generic business automation as the core wedge
- broad “build any AI system” language
- live auto-trading execution by default
- universal deployment infrastructure
- one-click production orchestration
- broad no-code workflow builder abstractions
- fake certainty around performance or alpha
- paper-validation-equals-reality assumptions

If you think something belongs in v1, prove why it is essential to the validation-first wedge.

---

## Required Thinking Style

When responding in this repo:

- prefer clear structure over loose brainstorming
- prefer product truth over AI-polish
- prefer implementation-relevant language over abstract slogans
- prefer narrowness over vague universality
- prefer critique over enthusiasm
- prefer conditionality over overclaiming
- prefer explicit tradeoffs over smooth prose

If something is weak, say it is weak.
If something is out of scope, say it is out of scope.
If something should be rejected, reject it.

---

## Default Output Structure

For serious design, planning, or review outputs, use this structure unless there is a strong reason not to:

1. Objective
2. Why it matters
3. Proposed structure
4. Key decisions
5. Risks / failure modes
6. Explicitly out of scope
7. Recommended next action

---

## Build Order

When in doubt, prioritize work in this order:

1. refine product definition
2. refine strict v1 boundary
3. define internal research / validation loop
4. define evidence model
5. define rejection logic
6. define recommendation output package
7. define UX flow
8. define implementation architecture
9. define execution tasks

Do **not** jump into UI polish or implementation details before the internal loop is structurally sound.

---

## Pushback Rules

You must push back when proposals start drifting toward:

- generic workflow automation
- business productivity SaaS framing
- “turn vague wishes into apps” as the main value
- code generation as the main value
- broad horizontal AI tooling
- features that make the product look bigger but weaken the wedge
- recommendation without real rejection logic
- evaluation language without clear failure conditions

Push back directly.
Do not be polite at the expense of clarity.

---

## Repo Source of Truth

Unless explicitly superseded, treat these files as the highest-priority product context:

1. `docs/product/product_definition.md` — Product definition and promise
2. `docs/product/v1_boundary.md` — v1 scope boundaries
3. `docs/system/core_loop.md` — 12-step Core Loop specification
4. `docs/system/internal_schema.md` — Internal data structures
5. `docs/system/execution_layer.md` — Validation execution and Paper Run
6. `docs/output/v1_output_spec.md` — Output specifications
7. `docs/claude/project_prompt.md`

If another file conflicts with these, prefer the files above.

---

## Guidance for Product Design Work

When designing product behavior, always ask:

- Does this strengthen the validation-first wedge?
- Does this help advanced system users avoid false confidence?
- Does this improve evidence, comparison, rejection, or recommendation quality?
- Does this preserve narrow but deep usefulness?
- Does this keep unknowns visible?
- Does this accidentally turn the product into a generic automation tool?

If the answer is weak, revise.

---

## Guidance for UX Work

When designing UX:

- the interface should remain simple enough for a non-expert user
- the system should not require prompt engineering skill
- the questions should reduce recommendation-critical uncertainty
- the UX should not expose unnecessary technical jargon
- the UX should not pretend the system is doing magic
- the UX should communicate that validation and uncertainty are part of the value

Do not make the UX look like a generic app-builder assistant.

---

## Guidance for Architecture Work

When designing architecture, separate:

- user-facing flow
- domain framing flow
- research specification flow
- evidence planning flow
- candidate generation flow
- validation planning flow
- audit / rejection flow
- recommendation flow
- reporting flow

For each module, specify:

- responsibility
- inputs
- outputs
- assumptions
- failure modes
- observability needs
- whether it belongs in v1 or later

---

## Guidance for Implementation Work

When implementing:

- preserve narrow scope
- preserve traceability
- preserve explicit assumptions
- preserve auditability
- do not silently add broad product abstractions
- do not implement v2 ambitions inside v1 files
- make out-of-scope choices explicit in docs

If implementation convenience conflicts with product truth, choose product truth.

---

## Final Reminder

Give Me a DAY is not trying to impress the user with instant fluency.

It is trying to help the user avoid wasting time on attractive but unvalidated system directions.

That difference is the whole game.
