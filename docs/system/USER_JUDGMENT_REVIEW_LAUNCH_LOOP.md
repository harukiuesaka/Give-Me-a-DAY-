# USER_JUDGMENT_REVIEW_LAUNCH_LOOP.md

**Purpose**: Critically evaluate the user's judgment that a launch/marketing/customer-feedback loop is needed before PMF.
**Date**: 2026-03-26
**Author**: Agent (Session 8)
**Input files read**:
- CLAUDE.md, CURRENT_STATE.md, SESSION_HANDOFF.md, OPEN_LOOPS.md, DECISIONS.md
- docs/system/REPO_FIT_ASSESSMENT_FACTORY_LAYER.md, docs/system/factory_layer_preconditions.md
- docs/state/product.md, docs/state/engineering.md, docs/state/ops.md
- docs/research/mom_test_run_plan.md, docs/implementation_status.md

---

## 1. User Claim Reconstruction

The user's position, synthesized from session history and stated intentions:

**Claim**: "The first launch should be a learning loop, not a finished product launch. To learn, the product must launch. To get customer voices, a marketing/acquisition loop is necessary even before PMF."

This decomposes into three sub-claims:

| # | Sub-claim | Type |
|---|-----------|------|
| A | The first launch is not a product launch — it is a learning instrument | Strategic framing |
| B | You cannot learn without launching something | Operational premise |
| C | Some form of marketing/acquisition loop must exist before PMF to generate the learning signal | Execution requirement |

The implied action chain: build a minimal launchable artifact → create acquisition channels (content, outreach, ads, etc.) → drive traffic → observe behavior → extract signal → iterate toward PMF.

---

## 2. Strongest Case For the User's Judgment

### 2.1 The learning-before-PMF loop is theoretically sound

The Lean Startup canon (Ries, Blank, Fitzpatrick) uniformly argues that customer signal must be gathered early, before product-market fit is confirmed. The user's instinct — that some form of external contact is necessary to learn — is directionally correct. Zero users means zero signal. Zero signal means all product decisions are internal projections.

**Repo evidence supporting this**: OL-016 is open with zero interviews. `docs/state/product.md` lists "Live user validation" as the first Unknown. CURRENT_STATE.md lists "No live users — PMF entirely unvalidated" as blocker #2. The repo itself acknowledges the learning gap.

### 2.2 The repo is at risk of indefinite internal optimization

The repo has completed 8 sessions of system, eval, state, and architecture work — all internal. No external human has seen the product. The eval pipeline is green (12/12). CI is green. State architecture is clean. The natural next internal optimization (factory layer, more evals, more state files) has already been assessed and deferred. The repo is approaching diminishing returns on internal work.

**Repo evidence**: `REPO_FIT_ASSESSMENT_FACTORY_LAYER.md` §7: "The correct next action is not factory-layer work. It is: Haruki: OL-016 (Mom Test)." The repo's own strategic assessment points outward.

### 2.3 The Mom Test requires access to real people, which requires some form of outreach

`docs/research/mom_test_run_plan.md` specifies: ≥3 interviews with quant researchers, systematic traders, or data scientists at financial institutions. These people do not appear spontaneously. Reaching them requires some form of deliberate outreach — cold email, warm introductions, community participation, or content that attracts attention. The user's claim that "some kind of acquisition loop" is needed is, at minimum, a recognition that interviews require outreach infrastructure.

---

## 3. Strongest Case Against the User's Judgment

### 3.1 "Launch loop" conflates two fundamentally different activities

There is a critical difference between:

- **Outreach for learning** (interviews, user research, cold DMs asking for 20 minutes of time)
- **Launch for acquisition** (landing pages, content marketing, ad campaigns, sign-up flows, onboarding funnels)

The user's framing — "marketing/acquisition loop" — implies the second. But OL-016 requires the first. A marketing/acquisition loop is infrastructure for scaling signal. What the repo needs right now is not scale — it is ≥3 conversations with the right people. Those conversations require outreach, not a loop.

**Repo evidence**: `mom_test_run_plan.md` §Outreach Note: "Outreach copy should ask for 20 minutes to learn about their strategy research process. It must not describe or sell the product." The plan explicitly rejects acquisition framing.

### 3.2 A "launch" implies a launchable artifact — which may be premature

The user's claim assumes there should be something to launch. But what? The backend pipeline produces a recommendation package for investment strategy validation. The frontend is a 5-page React app. Neither has been deployed to production. Neither has been tested with a real user.

Launching an untested artifact to generate learning signal is backwards. The Mom Test method specifically says: learn about the user's problem *before* showing them your solution. You learn more from a 20-minute conversation about their current workflow than from watching them click through an unpolished prototype.

**Repo evidence**: CLAUDE.md §Product Non-Negotiables #10: "v1 must stay narrow." D-001: "2-week goal locked to minimum loop establishment." The repo's own strategic framing does not support a launch at this stage.

### 3.3 Marketing/acquisition infrastructure has a maintenance cost with zero proven payoff

Building a content pipeline, landing page, email sequence, or social media presence requires ongoing effort. If the ICP is wrong (Unknown per `docs/state/product.md`), the messaging is wrong (Unknown per OL-016), and the product's value proposition is unvalidated — then every marketing asset built now will likely need to be rebuilt after customer validation.

The cost is not just the initial build. It is the ongoing maintenance of infrastructure that serves an unvalidated hypothesis.

---

## 4. Level Separation Analysis

The user's judgment contains claims at different levels of abstraction. Evaluating them requires separating the levels:

| Level | Claim | Verdict |
|-------|-------|---------|
| **Strategic** | "Learning requires external contact" | **Correct.** Indisputable. Zero users = zero signal. |
| **Tactical** | "External contact requires a launch" | **Incorrect.** External contact requires outreach. A launch is one form of outreach, and an expensive one. Interviews are another form — cheaper, higher signal density. |
| **Operational** | "A marketing/acquisition loop must be built" | **Premature.** A loop implies repeatable infrastructure. What is needed is ≥3 targeted conversations. Repeatable infrastructure is justified only after those conversations confirm the ICP and pain point. |
| **Execution** | "This should happen before PMF" | **Correct in direction, wrong in scope.** Customer contact before PMF: yes. Marketing loop before PMF: no. Customer research before PMF: yes. Acquisition funnel before PMF: no. |

The user is right at the strategic level and wrong at the operational level. The error is scope inflation: the correct action (talk to users) is being packaged inside a larger action (build a launch/marketing loop) that is not yet justified.

---

## 5. Repo-Specific Strategic Judgment

For Give Me a DAY specifically, the launch loop idea has an additional problem: **the product's ICP is unusually narrow and hard to reach**.

The target respondent profile (`mom_test_run_plan.md`) is: quant researchers, systematic traders, data scientists at financial institutions. These people:

- Do not browse Product Hunt or Hacker News looking for new tools
- Do not respond to generic "AI for investing" landing pages
- Are skeptical of claims and marketing language
- Value credibility and domain expertise over product polish
- Are reachable primarily through warm introductions, professional networks, or domain-specific communities (QuantConnect forums, EliteTrader, r/algotrading, specialized Slack/Discord groups, academic conferences)

A conventional launch loop (landing page → content → ads → signups) would attract the wrong audience for this product. The right audience is reached through:

1. Warm intros from people they trust
2. Credible domain content (not marketing content)
3. Direct outreach with a specific, non-salesy ask

This is not a loop. This is targeted, manual, high-touch outreach. It becomes a loop *after* the first 5–10 conversations reveal patterns worth systematizing.

---

## 6. What Is Actually Correct

The user is right about three things:

**6.1 The repo must make external contact.** Eight sessions of internal work with zero external human contact is a real problem. The eval pipeline is green, the state architecture is clean, and the next meaningful learning will not come from inside the repo. This is the user's core insight, and it is correct.

**6.2 Outreach requires deliberate effort, not passive waiting.** The target ICP will not find the product organically. Someone must actively reach out to potential respondents. The user is correct that this requires planning and execution, not just "we'll get to it eventually."

**6.3 The learning should start before the product is "ready."** Waiting for a polished, deployed, fully tested product before talking to users is a common startup mistake. The user's instinct to start learning now — with whatever exists — is correct. The product does not need to be ready for users. The *conversations* need to happen regardless of product readiness.

---

## 7. What Is Incorrect, Premature, or Oversized

**7.1 Framing interviews as a "launch" inflates scope and creates wrong expectations.** A launch implies something public, something users can access, something with a landing page. None of this is needed for Mom Test interviews. Calling it a launch creates pressure to build launch infrastructure — which is premature.

**7.2 A "marketing/acquisition loop" is infrastructure for a confirmed ICP — which does not exist yet.** Marketing works when you know who you are talking to, what pain you are addressing, and what language resonates. All three are Unknown for this repo. Building a loop before these are confirmed means building on sand.

**7.3 The assumption that you need a live product to learn is false for this stage.** The Mom Test method is explicitly designed to generate learning *without* showing the product. The 10 interview questions in `mom_test_run_plan.md` do not reference the product at all. The richest learning at this stage comes from understanding the respondent's current workflow, not from watching them use a prototype.

---

## 8. Smallest Justified Next-Step Layer

Given the repo's current state (eval green, state architecture clean, zero external contact, OL-016 open), the smallest justified next step is:

### Layer 0: Manual Outreach for Mom Test (no infrastructure)

| Component | Description | Cost | Justification |
|-----------|-------------|------|---------------|
| Respondent list | 10–15 names of quant researchers / systematic traders reachable by Haruki's network or cold outreach | 2–3 hours (human) | Cannot interview without names |
| Outreach copy | 3–4 sentence cold email / DM asking for 20 min conversation about their strategy research process | 30 min (agent draft, human approval) | `mom_test_run_plan.md` §Outreach Note already specifies format |
| Interview execution | 3–5 conversations, 20 min each | 1–2.5 hours (human) | OL-016 closure requires ≥3 |
| Notes capture | Use template from `mom_test_run_plan.md` | 15 min per interview (human) | Evidence must be Observed, not Inferred |
| Synthesis | Agent writes `mom_test_synthesis_01.md` after ≥3 interviews | 1 hour (agent) | Required for OL-016 closure |

**Total estimated cost**: 5–8 hours of Haruki's time over 1–2 weeks. Zero infrastructure. Zero marketing assets. Zero landing pages.

**What this produces**:
- OL-016 closure (or a clear rejection verdict with ICP revision)
- C1 (factory layer precondition) satisfied
- Evidence for or against the current ICP hypothesis
- Data to inform whether a marketing/acquisition loop is even the right next step

**What this does NOT produce** (and should not):
- A landing page
- A content calendar
- An email sequence
- Social media presence
- A sign-up flow
- Paid acquisition
- A "launch"

---

## 9. What Should NOT Be Built Yet

The following are explicitly premature until OL-016 is closed with confirmed findings:

| Item | Why premature |
|------|---------------|
| Landing page | Messaging requires confirmed ICP and pain point. Unknown today. |
| Content marketing pipeline | Content requires a confirmed audience. Unknown today. |
| Email nurture sequence | Nurture requires a confirmed value proposition. Unknown today. |
| Social media presence | Social requires a confirmed voice and audience. Unknown today. |
| Paid acquisition (ads) | Acquisition spend before ICP confirmation is waste. |
| Product demo / walkthrough | Demo requires a confirmed use case to demonstrate. Unknown today. |
| Referral or viral loop | Loop requires confirmed product-market fit to have anything to loop. |
| Analytics / tracking infrastructure | Analytics require users. Zero users today. |
| GTM module (factory layer) | `REPO_FIT_ASSESSMENT_FACTORY_LAYER.md` Collision 3: "Building automation to ship faster is premature when what to ship is unvalidated." |
| Public beta or early access program | Beta requires a deployable product with confirmed value. Neither confirmed. |

All of these become potentially justified *after* OL-016 closes with pain confirmation and ICP refinement. None of them are justified before.

---

## 10. Final Roadmap Recommendation

### Phase 1: Customer Research (NOW — next 1–2 weeks)

**Goal**: Close OL-016.
**Method**: Manual outreach → 3–5 Mom Test interviews → synthesis.
**Infrastructure required**: Zero. Email/DM + Zoom/phone + note-taking template.
**Decision gate**: OL-016 synthesis determines whether to proceed to Phase 2 or pivot ICP.

### Phase 2: Validated Outreach (AFTER OL-016 closes with pain confirmation)

**Goal**: Confirm that the product's recommendation package addresses the confirmed pain.
**Method**: Show the product to 2–3 respondents who confirmed the pain in Phase 1. Observe reactions. Record.
**Infrastructure required**: Minimal — deploy the existing frontend + backend to a URL Haruki can share. No landing page. No marketing. Direct link shared manually.
**Decision gate**: Do respondents recognize the product's output as addressing the pain they described?

### Phase 3: Repeatable Acquisition (AFTER Phase 2 confirms product-pain fit)

**Goal**: Build a lightweight, repeatable way to find more people like the confirmed ICP.
**Method**: Based on what worked in Phases 1–2 — community participation, content, referrals, or cold outreach. The method depends on what the interviews reveal about where these people spend time and what content they value.
**Infrastructure required**: Determined by Phase 2 findings. Not pre-buildable.
**Decision gate**: Can the acquisition method produce ≥5 qualified conversations per month?

### Phase 4: Launch Loop (AFTER Phase 3 demonstrates repeatable acquisition)

**Goal**: Systematize acquisition → onboarding → feedback → iteration.
**Method**: This is where the user's original "marketing/acquisition loop" becomes justified.
**Infrastructure required**: Landing page, content pipeline, onboarding flow, feedback mechanism, analytics.
**Decision gate**: D-001 re-scoped. Factory layer preconditions re-evaluated.

---

**Summary judgment**: The user's instinct to move outward is correct and timely. The user's proposed scope (marketing/acquisition loop) is 2–3 phases ahead of where the repo actually is. The correct action is Phase 1: manual outreach for Mom Test interviews. No infrastructure. No launch. No loop. Just conversations.
