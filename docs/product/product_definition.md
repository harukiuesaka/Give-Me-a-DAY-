# Product Definition

## One-line definition

Give Me a DAY is a validate-then-operate system that transforms AI reasoning into real-world outcomes; in v1, it does this for investment strategies by internally researching, testing, comparing, and rejecting candidate directions, presenting the 2 survivors to the user for approval, and operating the approved one under predefined stop conditions.

## Sharper line

Give Me a DAY does not hand you a plan.
It runs the plan for you — after proving it deserves to run.

## Why this product exists

Anyone can get a strategy idea in five minutes. The hard part comes after:

1. Is this idea actually supported by data, or does it just sound plausible?
2. Compared to what alternatives? Were the weak ones honestly rejected?
3. If it passes scrutiny, who builds the system, monitors it, knows when to stop?

Today these three problems are solved by three different products — research tools, backtesting platforms, and execution infrastructure — that don't talk to each other. The user is the glue. They must interpret backtests, decide which direction to pursue, wire up execution, define stop conditions, and remember to re-evaluate. Most don't.

Give Me a DAY replaces the user as the glue. It validates internally, presents externally, and operates autonomously — with the user's approval as the only gate between validation and operation.

Every validation and runtime outcome is also learning material: what failed, what survived, what conditions mattered, and which structures held up in reality. This is how the system improves over time at generating successful outputs, not just better reports.

## What the product does

### Internally (user does not see this)

- Receives a natural-language investment goal
- Reframes the goal as a testable research problem
- Generates 3–5 candidate strategy directions
- Acquires public data and runs backtests
- Performs statistical tests
- Compares candidates across multiple axes
- Audits each candidate for weak assumptions, data leakage, overfitting, unrealistic cost assumptions, regime dependency, and other failure patterns
- Rejects candidates that fail audit
- Selects the 2 strongest survivors (Primary and Alternative)

### Externally (user sees this)

- Presents 2 candidate cards: expected return band, estimated max loss, key risks, stop conditions, confidence level
- Requires explicit approval: user confirms risk awareness and selects one candidate
- Operates the approved candidate in Paper Run (simulated, no real money in v1)
- Monitors stop conditions daily and halts automatically when breached
- Sends monthly performance summaries
- Re-evaluates the strategy quarterly by re-running the internal pipeline with fresh data
- Requests re-approval when the recommendation changes

## What the product is

Give Me a DAY is a validate-then-operate system.

"Validate" means: research, backtest, compare, reject — all internally, with no user involvement in the process.

"Operate" means: run the approved strategy daily, monitor stop conditions, halt when necessary, re-evaluate periodically — all autonomously, with user approval as the only manual step.

The user's job is to state a goal, review 2 candidates, approve one, and check monthly reports. Everything else is the system's job.

## What the product is not

- A dashboard where users analyze backtests
- A tool that returns a recommendation for the user to implement
- A backtesting platform
- A code generator
- A robo-advisor that skips validation
- A trading terminal
- A generic AI workflow automation tool
- A broad "build anything with AI" system
- A productivity SaaS

## First wedge

- Investment strategy validation and operation (first domain pack)
- Japanese equities and US equities (v1)
- Daily-frequency strategies using public data
- Paper Run (simulated operation) in v1

## Product center

The product center is the **sequence**, not any single capability:

```
validate → present → approve → operate → monitor → re-evaluate → re-approve
```

Each step depends on and reinforces the others:

- Validate without operate = a plan the user must execute alone
- Operate without validate = a black box the user must trust blindly
- Operate without monitor = fire-and-forget risk
- Monitor without re-evaluate = passive observation without response
- Re-evaluate without re-approve = unauthorized change to what the user approved

No single step is the product. The unbroken chain is the product.

## Core truth

The hard part of investment strategy is not generating ideas or placing trades.

The hard part is:
- knowing which direction survives honest scrutiny
- knowing what the scrutiny couldn't cover
- knowing when to stop
- knowing when the world has changed enough to invalidate the direction
- having the discipline to halt and re-evaluate rather than hope

Most users lack the tools, time, or temperament to do this consistently. Give Me a DAY automates this discipline.

## Product promise

For a user with an investment goal, Give Me a DAY will:

1. Understand the goal from a single natural-language input
2. Internally research, test, compare, and reject candidate strategies — without requiring the user to participate in the process
3. Present the 2 strongest surviving candidates with expected return band, estimated max loss, key risks, stop conditions, and confidence level
4. Require explicit user approval before any operation begins
5. Operate the approved strategy autonomously in Paper Run (v1)
6. Automatically halt when predefined stop conditions are breached
7. Summarize performance monthly in plain language
8. Re-evaluate the strategy quarterly using fresh data
9. Request re-approval when the recommendation changes or a stop condition is triggered

## Product non-promise

- No guaranteed alpha, profitability, or positive returns
- No guarantee that Paper Run results predict real execution results
- No guarantee that past backtest performance continues
- No real-money execution in v1
- No universal coverage of all asset classes, markets, or frequencies
- No regulatory or tax advice
- No elimination of investment risk
- No permanent validity of any recommendation — all recommendations expire and require re-evaluation

---

**Role of this document**: This is the highest-level definition of what Give Me a DAY is, what it does, and what it promises. All other documents — boundary, schema, loop, execution, UX — must be consistent with this definition. If a downstream document contradicts this one, this document takes precedence.
