# Give Me a DAY v1 — Module Technical Design

**Document type**: Implementation-ready technical design
**Upstream**: product_definition.md, v1_boundary.md, v1_output_spec.md, internal_schema.md, core_loop.md, execution_layer.md
**Purpose**: Define each module's responsibility, interface, logic, and failure modes at a granularity sufficient for implementation

---

## Module Map

```
User ──→ [1] GoalIntake
              ↓
         [2] DomainFramer
              ↓
         [3] ResearchSpecCompiler
              ↓
         [4] CandidateGenerator ←── [5] EvidencePlanner
              ↓                          ↓
         [6] ValidationPlanner ←─────────┘
              ↓
         [7] ExecutionLayer (Validation)
              ↓
         [8] AuditEngine ──── reject? ──→ [4] (once)
              ↓
         [9] RecommendationEngine
              ↓
         [10] ReportingEngine ──→ User (2-card presentation)
              ↓
         User ──→ Approval Gate
              ↓
         [7] ExecutionLayer (Paper Run)
              ↓
         [10] ReportingEngine ──→ User (monthly report, notifications)
              ↓
         [8]+[9] Re-evaluation (quarterly)

All modules read/write via [11] PersistenceStore
```

---

## Module 1: GoalIntake

### Objective
Accept user's natural-language investment goal and minimal context, produce a valid UserIntent object.

### Why it matters
Every downstream module depends on UserIntent. Garbage in → garbage out at every subsequent step. GoalIntake is the quality gate for the entire pipeline. It must extract enough to start the pipeline without demanding expertise from the user.

### Inputs
| Input | Source | Required |
|-------|--------|----------|
| goal_text | User input (textarea) | Yes (min 10 chars) |
| success_criteria | User input (text, 1 line) | No (defaults to open_uncertainty) |
| risk_preference | User selection (4 options) | No (default: medium) |
| time_horizon | User selection (5 options) | No (default: one_week) |
| exclusions | User checkboxes + free text | No (default: empty) |

### Outputs
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| UserIntent | internal_schema §1 | PersistenceStore → DomainFramer |

### Internal logic

```python
def process_goal_intake(raw_input) -> UserIntent:
    # 1. Domain check
    domain = classify_domain(raw_input.goal_text)
    if domain != "investment_research":
        raise DomainOutOfScopeError(raw_input.goal_text)

    # 2. Summarize goal
    user_goal_summary = llm_summarize(raw_input.goal_text, max_sentences=2)

    # 3. Extract or default each field
    success_definition = raw_input.success_criteria or None
    risk_preference = raw_input.risk_preference or "medium"
    time_horizon = raw_input.time_horizon or "one_week"
    must_not_do = parse_exclusions(raw_input.exclusions)

    # 4. Populate open_uncertainties
    uncertainties = []
    if success_definition is None:
        uncertainties.append("success criteria not provided — system will use domain defaults")
        success_definition = generate_default_success(risk_preference)
    if raw_input.risk_preference is None:
        uncertainties.append("risk preference defaulted to medium")
    if raw_input.time_horizon is None:
        uncertainties.append("time horizon defaulted to one_week")

    # 5. Build and validate UserIntent
    intent = UserIntent(
        run_id=generate_uuid(),
        created_at=now_iso(),
        raw_goal=raw_input.goal_text,
        domain="investment_research",
        user_goal_summary=user_goal_summary,
        success_definition=success_definition,
        risk_preference=risk_preference,
        time_horizon_preference=time_horizon,
        must_not_do=must_not_do,
        available_inputs=[],  # system acquires data, not user
        open_uncertainties=uncertainties
    )
    validate_user_intent(intent)
    return intent
```

Key subroutines:
- `classify_domain()`: Keyword + context classification. Returns "investment_research" or rejects. Uses keyword list from Domain Framing spec (investment, 株, FX, ファクター, モメンタム, バリュー, etc.) + negative patterns (業務効率化, CRM, マーケティング).
- `generate_default_success()`: Based on risk_preference, produces conservative default. very_low → "preserve capital with minimal loss"; medium → "outperform benchmark after costs over 3+ years".
- `validate_user_intent()`: Checks all required fields non-null, domain = "investment_research", run_id is valid UUID.

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| LLM (Claude API) | External service | goal summarization, domain classification |
| PersistenceStore | Internal module | Store UserIntent |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| LLM unavailable for summarization | Medium | Fall back to first 100 chars of raw_goal as summary |
| Domain classification ambiguous | Low | Default to investment_research, add "domain classification uncertain" to open_uncertainties |
| Input too short (<10 chars) | Low | Return validation error to user, request more detail |
| Input is clearly non-investment | Low | Return domain-out-of-scope message to user |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `intake.domain_classification` | Track hit rate of investment vs non-investment inputs |
| `intake.fields_defaulted_count` | How many fields used defaults (quality indicator) |
| `intake.open_uncertainties_count` | Pipeline quality predictor |
| `intake.latency_ms` | Performance tracking |

### v1 implementation scope
- Single-screen input → UserIntent generation
- Domain classification via keyword + LLM
- Default value assignment for missing fields
- No follow-up questions (single-pass extraction)
- No data availability assessment at this stage

### Later expansion
- v1.5: Multi-turn clarification for ambiguous goals
- v1.5: User profile integration (returning users)
- v2: Multi-domain support beyond investment_research

---

## Module 2: DomainFramer

### Objective
Transform UserIntent into a DomainFrame: classify the strategy archetype, reframe the goal as a testable research problem, decompose into falsifiable claims.

### Why it matters
This is the transformation from "what the user wants" to "what can be verified." Without DomainFrame, candidates are generated against a vague wish instead of a structured research problem. testable_claims drive the entire validation pipeline — they determine what tests to run and what constitutes failure.

### Inputs
| Input | Source |
|-------|--------|
| UserIntent | PersistenceStore |

### Outputs
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| DomainFrame | internal_schema §2 | PersistenceStore → ResearchSpecCompiler, CandidateGenerator |

### Internal logic

```python
def frame_domain(intent: UserIntent) -> DomainFrame:
    # 1. Classify archetype
    archetype = classify_archetype(intent.raw_goal, intent.user_goal_summary)
    # Returns: FACTOR | STAT_ARB | EVENT | MACRO | ML_SIGNAL | ALT_DATA | HYBRID | UNCLASSIFIED

    # 2. Reframe problem
    reframed = reframe_as_research_question(
        goal=intent.user_goal_summary,
        archetype=archetype,
        success_def=intent.success_definition,
        constraints=intent.must_not_do
    )
    # Template: "Whether [approach] is verifiable in [market] under [constraints]
    #            with respect to [success metric]"

    # 3. Generate core hypothesis
    hypothesis = extract_core_hypothesis(reframed)

    # 4. Decompose into testable claims
    claims = generate_claims(archetype, reframed, intent.success_definition)
    # Must produce: ≥1 premise, ≥1 core, ≥1 practical
    # Each claim must have falsification_condition

    # 5. Extract regime dependencies
    regimes = extract_regime_dependencies(archetype, intent.raw_goal)
    if len(regimes) == 0:
        regimes = ["market_trend_direction", "volatility_environment"]  # forced defaults

    # 6. Find comparable approaches
    comparables = match_known_approaches(archetype, reframed)

    # 7. Extract critical assumptions
    assumptions = extract_assumptions(archetype, reframed, intent.open_uncertainties)

    frame = DomainFrame(
        run_id=intent.run_id,
        archetype=archetype,
        reframed_problem=reframed,
        core_hypothesis=hypothesis,
        testable_claims=claims,
        critical_assumptions=assumptions,
        regime_dependencies=regimes,
        comparable_known_approaches=comparables
    )
    validate_domain_frame(frame)
    return frame
```

Key subroutines:
- `classify_archetype()`: LLM-based classification with keyword hints. Uses the 7-archetype taxonomy from Domain Framing spec. HYBRID if multiple archetypes detected; UNCLASSIFIED if none match.
- `generate_claims()`: Archetype-specific claim templates. Each archetype has a fixed template set (see Domain Framing spec §3). LLM fills template variables using the reframed problem and success definition.
- `validate_domain_frame()`: Checks: ≥1 claim per layer, all claims have falsification_condition, regime_dependencies non-empty, comparable_known_approaches ≥1 (except UNCLASSIFIED).

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| LLM (Claude API) | External | Archetype classification, problem reframing, claim generation |
| Domain Knowledge Base | Internal (static) | Archetype templates, claim patterns, known approaches catalog |
| PersistenceStore | Internal | Read UserIntent, store DomainFrame |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| LLM fails to classify archetype | Medium | Default to UNCLASSIFIED, use generic claim templates |
| LLM generates claims without falsification_condition | High | Retry once with explicit instruction. If still missing, reject claim and log |
| No comparable approaches found | Low | Set to empty for UNCLASSIFIED; for typed archetypes, use closest match from catalog |
| reframed_problem is not in question form | Low | Post-process: append "…か" or "?" if missing |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `framing.archetype_distribution` | Which archetypes users request (product insight) |
| `framing.claims_per_layer` | Completeness of decomposition |
| `framing.unclassified_rate` | How often classification fails (knowledge base gap indicator) |
| `framing.latency_ms` | Performance |

### v1 implementation scope
- 7 archetype classification
- 3-layer claim decomposition per archetype template
- Static knowledge base (no external search)
- Single-pass framing (no user confirmation step)

### Later expansion
- v1.5: Academic paper search for comparable_known_approaches
- v1.5: User confirmation checkpoint after framing
- v2: Custom archetype definition by user

---

## Module 3: ResearchSpecCompiler

### Objective
Consolidate UserIntent and DomainFrame into a single ResearchSpec that governs all downstream modules.

### Why it matters
ResearchSpec is the contract between framing and execution. It defines what must be tested, what evidence is needed, and what constitutes disqualifying failure. Without it, each downstream module makes independent assumptions about scope and standards.

### Inputs
| Input | Source |
|-------|--------|
| UserIntent | PersistenceStore |
| DomainFrame | PersistenceStore |

### Outputs
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| ResearchSpec | internal_schema §3 | PersistenceStore → EvidencePlanner, CandidateGenerator, ValidationPlanner, AuditEngine |

### Internal logic

```python
def compile_spec(intent: UserIntent, frame: DomainFrame) -> ResearchSpec:
    # 1. Derive minimum evidence standard
    evidence_standard = derive_evidence_standard(
        intent.risk_preference, intent.time_horizon_preference
    )
    # very_low risk → strong
    # low + quality_over_speed → strong
    # medium → moderate
    # high + fast → weak (with warning)
    # else → moderate

    # 2. Build assumption space from frame + domain defaults
    assumptions = build_assumption_space(
        frame.critical_assumptions,
        frame.archetype,
        intent.open_uncertainties
    )
    # Adds domain-default assumptions (market efficiency, stationarity,
    # liquidity, data quality, causal, cost, regulatory)
    # Max 15 items

    # 3. Derive disqualifying failures from testable claims
    failures = derive_disqualifying_failures(
        frame.testable_claims,
        intent.success_definition,
        evidence_standard
    )
    # Maps falsification_conditions to metric + threshold pairs

    # 4. Compile constraints
    constraints = compile_constraints(intent)

    # 5. Set evidence requirements (category-level, detailed in EvidencePlanner)
    evidence_reqs = infer_evidence_requirements(frame.archetype, frame.testable_claims)

    return ResearchSpec(
        spec_id=f"{intent.run_id}-RS",
        run_id=intent.run_id,
        primary_objective=f"Verify: {frame.core_hypothesis}",
        secondary_objectives=extract_secondary_objectives(frame),
        problem_frame=frame.reframed_problem,
        assumption_space=assumptions,
        constraints=constraints,
        evidence_requirements=evidence_reqs,
        validation_requirements={
            "must_test": [c.claim for c in frame.testable_claims],
            "must_compare": ["baseline_candidate"],
            "disqualifying_failures": failures,
            "minimum_evidence_standard": evidence_standard
        },
        recommendation_requirements={
            "must_return_runner_up": True,
            "must_return_rejections": True,
            "must_surface_unknowns": True,
            "allow_no_valid_candidate": True
        }
    )
```

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| Domain assumption checklist | Internal (static) | Default assumptions per archetype |
| PersistenceStore | Internal | Read intent + frame, store spec |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| Cannot map falsification_condition to metric+threshold | Medium | Store as prose-only failure with warning. AuditEngine will flag as imprecise |
| assumption_space exceeds 15 items | Low | Truncate to 15, prioritizing user-stated and critical assumptions |
| evidence_requirements cannot be inferred from archetype | Medium | Use generic evidence set (price + metadata minimum) |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `spec.evidence_standard` | Correlation with downstream confidence levels |
| `spec.disqualifying_failure_count` | How strict the validation bar is |
| `spec.assumption_count` | Complexity indicator |

### v1 implementation scope
- Mechanical derivation (no LLM needed for this module)
- Static assumption checklist per archetype
- Hardcoded recommendation_requirements (all true)

### Later expansion
- v1.5: User-adjustable evidence standard
- v2: Per-candidate custom disqualifying_failures

---

## Module 5: EvidencePlanner

### Objective
For each candidate, identify required evidence items, assess availability, detect biases, evaluate proxy options, and produce an EvidencePlan with coverage metrics.

### Why it matters
Evidence quality determines validation quality. EvidencePlanner prevents the pipeline from running tests on data it doesn't have, with biases it hasn't identified, or with proxy assumptions it hasn't evaluated. Every undetected evidence problem becomes an Audit issue downstream.

### Inputs
| Input | Source |
|-------|--------|
| ResearchSpec | PersistenceStore |
| Candidate[] | PersistenceStore |
| Acquired data (from Execution Layer) | DataStore |

### Outputs
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| EvidencePlan (per candidate) | internal_schema §5 | PersistenceStore → ValidationPlanner, AuditEngine |
| DataQualityReport[] | internal_schema §15 | PersistenceStore → AuditEngine |

### Internal logic

```python
def plan_evidence(spec: ResearchSpec, candidate: Candidate, acquired_data: dict) -> EvidencePlan:
    # 1. Generate evidence items from candidate requirements
    items = generate_evidence_items(candidate, spec.evidence_requirements)
    # Each item: category (from Evidence Taxonomy), description, requirement_level

    # 2. Assess availability against acquired data
    for item in items:
        item.availability = check_availability(item, acquired_data)
        item.quality_concerns = run_quality_assessment(item, acquired_data)
        item.known_biases = scan_bias_checklist(item.category, acquired_data)
        item.point_in_time_status = assess_pit_status(item, acquired_data)
        item.reporting_lag_days = estimate_reporting_lag(item)
        item.leakage_risk_patterns = identify_leakage_patterns(item)
        item.proxy_option = evaluate_proxy(item) if item.availability != "available" else None

    # 3. Identify critical gaps
    gaps = identify_critical_gaps(items)

    # 4. Compute gap severity
    gap_severity = compute_gap_severity(items)

    # 5. Compute coverage metrics
    coverage = compute_coverage(items)

    return EvidencePlan(
        evidence_plan_id=f"{spec.run_id}-EP-{candidate.candidate_id}",
        candidate_id=candidate.candidate_id,
        evidence_items=items,
        critical_gaps=gaps,
        gap_severity=gap_severity,
        coverage_metrics=coverage
    )
```

Key subroutines:
- `scan_bias_checklist()`: For each evidence category (PRC, FND, ALT, MAC, SNT, FLW, MTA), runs the bias patterns from Evidence Taxonomy (PRC-B01 through MTA-B05). Returns list of matched bias IDs.
- `identify_leakage_patterns()`: Cross-references item properties (PIT status, reporting lag, category) with Audit Rubric LKG-01 through LKG-07. Pre-flags potential leakage issues.
- `evaluate_proxy()`: Applies Evidence Taxonomy proxy rules. Returns `permitted: true/false` with `prohibition_reason` if not permitted.

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| Evidence Taxonomy | Internal (static) | Bias checklists, proxy rules per category |
| Execution Layer (DataAcquisition) | Internal module | Provides acquired data for availability assessment |
| PersistenceStore | Internal | Read spec + candidates, store plans |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| Data acquisition failed for all items | High | Set all availability = "unavailable", gap_severity = "blocking", add caveat |
| Bias scan returns false positives | Low | All flagged biases go to Audit for final judgment. False positives are filtered there |
| PIT assessment is uncertain | Medium | Default to "partial", add to open_uncertainties |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `evidence.coverage_percentage` per candidate | Key quality indicator |
| `evidence.gap_severity` per candidate | Blocks downstream validation if blocking |
| `evidence.bias_flags_count` | Volume of bias concerns feeding into Audit |
| `evidence.pit_none_count` | Leakage risk exposure |

### v1 implementation scope
- 7-category evidence assessment (PRC/FND/ALT/MAC/SNT/FLW/MTA)
- Bias scan using static checklist (no ML-based detection)
- Proxy evaluation using static rules
- Integration with DataAcquisition module for availability assessment

### Later expansion
- v1.5: Paid data source availability checking
- v1.5: Automated data procurement recommendations
- v2: Dynamic bias detection using statistical tests on acquired data

---

## Module 4: CandidateGenerator

### Objective
Generate 3–5 genuinely different strategy candidates based on the ResearchSpec and DomainFrame.

### Why it matters
Candidate diversity is the foundation of comparison and rejection. If candidates are too similar, comparison is meaningless and rejection has no teeth. The generator must produce at least one baseline (simplest known approach), one conservative (lower risk), and one exploratory (higher novelty), ensuring the final 2-card presentation offers a real choice.

### Inputs
| Input | Source |
|-------|--------|
| ResearchSpec | PersistenceStore |
| DomainFrame | PersistenceStore |
| Rejection constraints (if re-run after all-rejection) | AuditEngine |

### Outputs
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| Candidate[] (3–5 objects) | internal_schema §4 | PersistenceStore → EvidencePlanner, ValidationPlanner, AuditEngine |

### Internal logic

```python
def generate_candidates(spec: ResearchSpec, frame: DomainFrame,
                        rejection_constraints: list = None) -> list[Candidate]:
    archetype = frame.archetype

    # 1. Generate baseline candidate (simplest known approach)
    baseline = generate_from_template(
        archetype=archetype,
        candidate_type="baseline",
        constraints=spec.constraints,
        rejection_constraints=rejection_constraints
    )

    # 2. Generate conservative candidate
    conservative = generate_from_template(
        archetype=archetype,
        candidate_type="conservative",
        constraints=spec.constraints,
        bias_toward="lower_risk_lower_complexity",
        rejection_constraints=rejection_constraints
    )

    # 3. Generate exploratory candidate
    exploratory = generate_from_template(
        archetype=archetype,
        candidate_type="exploratory",
        constraints=spec.constraints,
        bias_toward="higher_novelty",
        rejection_constraints=rejection_constraints
    )

    candidates = [baseline, conservative, exploratory]

    # 4. Optional: generate hybrid if archetype suggests it
    if archetype == "HYBRID" or diversity_score(candidates) < 0.7:
        hybrid = generate_from_template(
            archetype=archetype,
            candidate_type="hybrid",
            constraints=spec.constraints
        )
        candidates.append(hybrid)

    # 5. Diversity check
    for i, c1 in enumerate(candidates):
        for c2 in candidates[i+1:]:
            overlap = compute_architecture_overlap(c1, c2)
            if overlap > 0.70:
                raise InsufficientDiversityError(c1, c2, overlap)

    # 6. Validate each candidate
    for c in candidates:
        assert len(c.core_assumptions) > 0
        assert len(c.known_risks) > 0
        assert all(a.failure_impact for a in c.core_assumptions)

    return candidates
```

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| LLM (Claude API) | External | Generate candidate summaries, architecture outlines, assumption articulation |
| Archetype template library | Internal (static) | Baseline definitions per archetype |
| PersistenceStore | Internal | Read spec + frame, store candidates |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| LLM generates <3 candidates | High | Retry with explicit count instruction. If still <3, generate baseline + 2 variations mechanically |
| Diversity check fails (overlap >70%) | Medium | Regenerate the overlapping candidate with explicit differentiation constraint |
| Candidates violate must_not_do | High | Post-generation filter: reject any candidate whose architecture_outline contains forbidden behaviors |
| All candidates identical to rejection_constraints input | Medium | Widen archetype scope (try adjacent archetypes) |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `candidates.count` | Should be 3–5 |
| `candidates.diversity_score` | Must be ≥0.3 (1.0 = completely different) |
| `candidates.type_distribution` | Must include baseline + conservative + exploratory |
| `candidates.generation_latency_ms` | Performance |

### v1 implementation scope
- LLM-generated candidates from archetype templates
- 3–5 candidates per run
- Diversity enforcement via architecture overlap check
- must_not_do enforcement

### Later expansion
- v1.5: User-submitted candidate (user can add their own direction for comparison)
- v2: Multi-archetype candidate generation (mix FACTOR + MACRO etc.)

---

## Module 6: ValidationPlanner

### Objective
For each candidate, define the test sequence, metrics, pass/fail thresholds, and comparison framework.

### Why it matters
The validation plan is what makes rejection meaningful. Without explicit failure conditions, every candidate "passes." Without comparison targets, there is no basis for ranking. The plan must be complete enough that the Execution Layer can run tests mechanically.

### Inputs
| Input | Source |
|-------|--------|
| ResearchSpec | PersistenceStore |
| Candidate[] | PersistenceStore |
| EvidencePlan[] | PersistenceStore |

### Outputs
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| ValidationPlan (per candidate) | internal_schema §6 | PersistenceStore → ExecutionLayer, AuditEngine |

### Internal logic

```python
def plan_validation(spec: ResearchSpec, candidate: Candidate,
                    evidence: EvidencePlan) -> ValidationPlan:
    tests = []

    # 1. Mandatory tests (always included)
    tests.append(build_test("offline_backtest", candidate, spec, evidence))
    tests.append(build_test("out_of_sample", candidate, spec, evidence))
    tests.append(build_test("walk_forward", candidate, spec, evidence))
    tests.append(build_test("regime_split", candidate, spec, evidence))

    # 2. Conditional tests
    if candidate.validation_burden != "low":
        tests.append(build_test("sensitivity", candidate, spec, evidence))

    # 3. Set execution prerequisites (DAG)
    tests[1].execution_prerequisites = [tests[0].test_id]  # OOS requires backtest
    tests[2].execution_prerequisites = [tests[0].test_id]  # WF requires backtest
    tests[3].execution_prerequisites = [tests[0].test_id]  # Regime requires backtest

    # 4. Map disqualifying_failures to test metrics
    for test in tests:
        for failure in spec.validation_requirements.disqualifying_failures:
            if failure.applies_to in ["all_candidates", candidate.candidate_type]:
                link_failure_to_metric(test, failure)

    # 5. Determine plan completeness
    completeness = "complete"
    if evidence.gap_severity == "manageable":
        completeness = "partial_due_to_evidence_gaps"
    elif evidence.gap_severity == "blocking":
        completeness = "minimal"

    # 6. Build comparison matrix
    matrix = build_comparison_matrix(spec.validation_requirements.must_compare)

    # 7. Validate: every test has ≥1 failure condition
    for test in tests:
        assert len(test.failure_conditions) >= 1, f"Test {test.test_id} has no failure conditions"

    return ValidationPlan(
        validation_plan_id=f"{spec.run_id}-VP-{candidate.candidate_id}",
        candidate_id=candidate.candidate_id,
        test_sequence=tests,
        plan_completeness=completeness,
        comparison_matrix=matrix
    )
```

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| Test template library | Internal (static) | Default configurations for each test type |
| PersistenceStore | Internal | Read spec + candidates + evidence, store plans |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| Evidence gap makes a test impossible | Medium | Mark test as "skipped_due_to_evidence", reduce plan_completeness |
| disqualifying_failure cannot map to any test metric | Medium | Store as unlinked failure, flag for Audit |
| Test count exceeds execution budget (time_horizon=fast) | Low | Prioritize: backtest > OOS > regime > WF > sensitivity. Drop lowest priority |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `validation.test_count` per candidate | Correlates with execution time |
| `validation.plan_completeness` | Quality gate for confidence calculation |
| `validation.failure_conditions_total` | Must be ≥ test_count (each test has ≥1) |

### v1 implementation scope
- 5 test types (backtest, OOS, walk-forward, regime, sensitivity)
- Static test templates with parameterized thresholds
- DAG-based prerequisite ordering
- Mechanical plan_completeness derivation

### Later expansion
- v1.5: Monte Carlo simulation tests
- v1.5: Custom stress test scenarios
- v2: User-defined test configurations

---

## Module 7: ExecutionLayer

### Objective
Execute validation tests on real data (Validation Execution phase) and operate the approved strategy daily (Paper Run phase).

### Why it matters
This is the module that separates Give Me a DAY from a planning tool. Without execution, the product outputs hypothetical assessments. With execution, it outputs evidence-backed judgments and a running system.

### Inputs

**Validation Execution phase**:
| Input | Source |
|-------|--------|
| ValidationPlan[] | PersistenceStore |
| EvidencePlan[] (with acquired data) | PersistenceStore + DataStore |

**Paper Run phase**:
| Input | Source |
|-------|--------|
| Approval | PersistenceStore |
| Candidate (approved) | PersistenceStore |

### Outputs

**Validation Execution phase**:
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| TestResult[] | internal_schema §16 | PersistenceStore → AuditEngine |
| ComparisonResult | internal_schema §17 | PersistenceStore → AuditEngine, RecommendationEngine |

**Paper Run phase**:
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| PaperRunState | internal_schema §12 | PersistenceStore → ReportingEngine |
| MonthlyReport | internal_schema §13 | PersistenceStore → User (via notification) |
| ReEvaluationResult | internal_schema §14 | PersistenceStore → ReportingEngine |

### Internal logic

**Validation Execution**: See execution_layer.md for detailed BacktestEngine architecture, statistical test suite, comparison engine, and execution-informed audit adapter.

**Paper Run daily cycle**:
```python
def run_daily_cycle(paper_run: PaperRunState, candidate: Candidate):
    # 1. Acquire today's data
    data = fetch_daily_data(paper_run.candidate_id)
    quality = check_data_quality(data)
    if quality.consecutive_failures >= 3:
        trigger_stop_condition("SC-04", paper_run)
        return

    # 2. Calculate signals
    signals = calculate_signals(candidate, data)
    if detect_anomaly(signals, paper_run.signal_history):
        trigger_stop_condition("SC-03", paper_run)
        return

    # 3. Rebalance if scheduled
    if is_rebalance_date(paper_run):
        trades = generate_trades(signals, paper_run.portfolio, candidate)
        trades_with_costs = apply_cost_model(trades, paper_run.runtime_config.cost_model)
        execute_virtual_trades(trades_with_costs, paper_run)

    # 4. Update portfolio
    update_mark_to_market(paper_run, data)

    # 5. Check stop conditions
    check_all_stop_conditions(paper_run)

    # 6. Persist
    save_daily_snapshot(paper_run)
```

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| yfinance | External library | Daily OHLCV acquisition |
| fredapi | External library | Macro indicator acquisition |
| numpy / scipy / statsmodels | External libraries | Backtest computation, statistical tests |
| Scheduler (cron) | Infrastructure | Paper Run daily trigger |
| PersistenceStore | Internal | Read plans, store results + state |
| NotificationService | Internal | Alert user on stop conditions |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| API rate limit during data acquisition | Medium | Retry with exponential backoff. After 3 retries, mark as failed, use last available data |
| Backtest timeout (>300s) | Medium | Return partial results. Mark test as partial |
| All backtests fail | High | Fall back to planning-only mode. confidence capped at low |
| Paper Run daily data fetch fails | Medium | Use last available data. If 3 consecutive days fail → SC-04 |
| Paper Run signal calculation error | High | Pause Paper Run, notify user as anomaly |
| Market holiday detection failure | Low | Detect via zero-volume check. Skip processing on detected holidays |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `execution.validation.tests_completed` | Must equal test_count per candidate |
| `execution.validation.total_latency_ms` | User wait time predictor |
| `execution.paper_run.daily_cycle_latency_ms` | System health |
| `execution.paper_run.stop_condition_proximity` | Safety monitoring |
| `execution.paper_run.data_acquisition_failures` | SC-04 early warning |
| `execution.paper_run.signal_anomaly_score` | SC-03 early warning |

### v1 implementation scope
- **Validation**: Backtest, OOS, walk-forward, regime-split, sensitivity, statistical tests, comparison
- **Paper Run**: Daily cycle, 4 stop conditions, monthly report trigger, quarterly re-evaluation trigger
- Public data only (Yahoo Finance, FRED, CFTC)
- Daily frequency only
- Max 20 years / 500 instruments

### Later expansion
- v1.5: Broker API integration for real execution
- v1.5: Paid data source integration
- v1.5: ML model training/inference pipeline
- v2: Intraday signal calculation

---

## Module 8: AuditEngine

### Objective
Examine every candidate for weaknesses across 10 categories, assign severity to each issue, determine disqualification, and produce a complete Audit object.

### Why it matters
This is the product's core differentiator. The quality of rejection determines the quality of recommendation. A lenient Audit that passes everything makes the product worthless. A well-calibrated Audit that rejects attractive-but-fragile candidates is the product's value proposition.

### Inputs
| Input | Source |
|-------|--------|
| Candidate[] | PersistenceStore |
| EvidencePlan[] | PersistenceStore |
| ValidationPlan[] | PersistenceStore |
| TestResult[] (if available) | PersistenceStore |
| ComparisonResult (if available) | PersistenceStore |
| ResearchSpec | PersistenceStore |

### Outputs
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| Audit (per candidate) | internal_schema §7 | PersistenceStore → RecommendationEngine, ReportingEngine |

### Internal logic

```python
def audit_candidate(candidate, evidence, validation, test_results,
                    comparison, spec) -> Audit:
    issues = []

    # Phase 1: Data integrity
    issues += scan_evidence_gaps(evidence, spec)           # EVD-01 to EVD-06
    issues += scan_leakage_risks(evidence, candidate)      # LKG-01 to LKG-07

    # Phase 2: Methodological soundness
    issues += scan_assumptions(candidate, spec)            # ASM-01 to ASM-07
    issues += scan_overfitting(candidate, validation, test_results)  # OVF-01 to OVF-06
    issues += scan_regime_dependency(candidate, evidence, test_results)  # RGM-01 to RGM-05

    # Phase 3: Practical viability
    issues += scan_realism(candidate, test_results)        # RLM-01 to RLM-07
    issues += scan_cost_assumptions(candidate, evidence)   # CST-01 to CST-04
    issues += scan_complexity(candidate, spec)             # CMP-01 to CMP-05
    issues += scan_observability(candidate)                # OBS-01 to OBS-04

    # Phase 4: Meta evaluation
    issues += scan_recommendation_risk(candidate, issues)  # RCR-01 to RCR-05
    issues += check_compound_patterns(issues)              # Cross-category combinations

    # Execution-informed severity adjustment (if test results exist)
    if test_results:
        issues = adjust_severity_from_execution(issues, test_results)

    # FC-01: Zero-issue check
    if len(issues) == 0:
        issues = rerun_critical_categories(candidate, evidence)
        # Force re-scan of assumption, leakage_risk, realism

    # Determine audit status
    status = determine_status(issues)
    rejection_reason = build_rejection_reason(issues) if status == "rejected" else None
    surviving = extract_surviving_assumptions(candidate, issues) if status != "rejected" else []

    return Audit(
        candidate_id=candidate.candidate_id,
        audit_status=status,
        issues=issues,
        rejection_reason=rejection_reason,
        surviving_assumptions=surviving,
        residual_risks=extract_residual_risks(issues),
        meta_audit=build_meta_audit(issues)
    )
```

Key subroutines:
- `determine_status()`: any disqualifying → rejected; ≥3 high → passed_with_warnings; critical with mitigation → passed_with_warnings; else → passed.
- `check_compound_patterns()`: 5 compound patterns from Audit Rubric Appendix C ("見せかけの好成績", "検証不能な複雑性", "コスト死", "レジーム盲点", "過学習パッケージ").
- `adjust_severity_from_execution()`: Uses execution_layer.md severity adjustment rules (OOS Sharpe ratio, cost-adjusted returns, regime performance, PIT compliance).

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| Audit Rubric (48 patterns) | Internal (static) | Pattern definitions, severity logic, disqualifying logic |
| FC rules (FC-01 to FC-06) | Internal (static) | False confidence prevention |
| PersistenceStore | Internal | Read all upstream objects, store Audit |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| Pattern scan produces too many false positives | Medium | All issues go through severity thresholds. Low-severity issues don't affect status |
| Compound pattern detection is too aggressive | Medium | Compound patterns only upgrade severity, never directly disqualify without individual high-severity components |
| No TestResults available (execution failed) | Medium | Fall back to plan-based mode. Add caveat "audit based on plan-level assessment only" |
| All candidates rejected on first pass | Expected | Trigger re-generation loop: return to CandidateGenerator with rejection constraints |
| All candidates rejected on second pass | Expected | Proceed with best_candidate_id = null. This is valid output |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `audit.rejection_rate` | Should be >0% and <100% in normal operation |
| `audit.issues_per_candidate` | Zero-issue flag monitoring |
| `audit.severity_distribution` | Calibration check |
| `audit.compound_patterns_fired` | Advanced pattern detection monitoring |
| `audit.mode` (plan-based / execution-informed) | Track execution coverage |

### v1 implementation scope
- 10 categories, 48 patterns (Tier 1 mandatory, Tier 2 strongly recommended)
- Compound pattern detection (5 patterns)
- FC-01 through FC-06
- Execution-informed severity adjustment when TestResults exist
- Single re-generation loop on all-rejection

### Later expansion
- v1.5: Execution-result-based Audit (actual backtest numbers driving severity)
- v1.5: Meta-audit (audit of audit quality)
- v2: Custom audit rubrics per domain

---

## Module 9: RecommendationEngine

### Objective
Select Primary and Alternative from surviving candidates, produce a Recommendation with ranking logic, conditions, unknowns, and expiry.

### Why it matters
This is the final judgment layer before the user sees anything. It must compress all upstream information into a ranking that is transparent (ranking_logic with ≥3 axes), conditional (critical_conditions non-empty), and honest (open_unknowns non-empty, confidence mechanically determined).

### Inputs
| Input | Source |
|-------|--------|
| Audit[] | PersistenceStore |
| Candidate[] | PersistenceStore |
| ComparisonResult | PersistenceStore |
| ResearchSpec | PersistenceStore |
| EvidencePlan[] | PersistenceStore |

### Outputs
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| Recommendation | internal_schema §8 | PersistenceStore → ReportingEngine |

### Internal logic

```python
def generate_recommendation(audits, candidates, comparison, spec, evidence_plans) -> Recommendation:
    # 1. Filter to surviving candidates
    survivors = [c for c, a in zip(candidates, audits)
                 if a.audit_status in ("passed", "passed_with_warnings")]
    rejected = [c for c, a in zip(candidates, audits)
                if a.audit_status == "rejected"]

    # 2. Handle 0-survivor case
    if len(survivors) == 0:
        return build_null_recommendation(rejected, spec)

    # 3. Rank survivors
    ranking = rank_candidates(survivors, comparison, audits)
    # Uses 6-axis comparison: validation_feasibility, assumption_robustness,
    # implementation_complexity, regime_sensitivity, validation_cost, novelty
    # Each axis has per-candidate assessment and verdict

    best = ranking[0]
    runner_up = ranking[1] if len(ranking) > 1 else None

    # 4. Enforce type diversity (Primary ≠ Alternative candidate_type)
    if runner_up and best.candidate_type == runner_up.candidate_type:
        runner_up = find_different_type_runner_up(ranking)

    # 5. Calculate confidence (FC-02, mechanical)
    coverage = get_best_coverage(evidence_plans, best)
    audit_issues = get_audit(audits, best)
    confidence = calculate_confidence_fc02(coverage, audit_issues)

    # 6. Extract conditions and unknowns
    conditions = derive_conditions(audit_issues.surviving_assumptions, spec.assumption_space)
    unknowns = derive_unknowns(evidence_plans, audit_issues, spec)

    # Validation: conditions non-empty, unknowns non-empty
    assert len(conditions) >= 1, "Unconditional recommendations do not exist"
    assert len(unknowns) >= 1, "Zero unknowns at plan stage is unrealistic"

    # 7. Set expiry
    expiry = calculate_expiry(spec.time_horizon_preference)

    return Recommendation(
        run_id=spec.run_id,
        best_candidate_id=best.candidate_id,
        runner_up_candidate_id=runner_up.candidate_id if runner_up else None,
        rejected_candidate_ids=[c.candidate_id for c in rejected],
        ranking_logic=ranking.logic,  # ≥3 axes, no "overall judgment"
        open_unknowns=unknowns,
        critical_conditions=conditions,
        confidence_label=confidence,
        confidence_explanation=explain_confidence(confidence, coverage, audit_issues),
        next_validation_steps=derive_next_steps(conditions, unknowns),
        recommendation_expiry=expiry
    )
```

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| FC-02 confidence rules | Internal (static) | Mechanical confidence determination |
| FC-03 ranking rules | Internal (static) | No "overall judgment" allowed |
| PersistenceStore | Internal | Read upstream objects, store Recommendation |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| Only 1 survivor (no runner-up possible) | Low | runner_up_candidate_id = null. Output 1-card presentation |
| Type diversity cannot be achieved (all survivors same type) | Low | Accept same type, add caveat "alternative has similar approach" |
| confidence_label = high (suspiciously high at plan stage) | Medium | Trigger FC calibration warning in observability logs |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `recommendation.confidence_distribution` | high > 10% → calibration alarm |
| `recommendation.null_rate` | How often all candidates are rejected |
| `recommendation.conditions_count` | Typically 2–5 |
| `recommendation.unknowns_count` | Typically 1–4 |

### v1 implementation scope
- 6-axis ranking
- FC-02 mechanical confidence
- Expiry calculation from time_horizon_preference
- Null recommendation with alternative directions

### Later expansion
- v1.5: Historical confidence calibration (compare predicted vs actual performance)
- v2: Multi-strategy portfolio recommendation

---

## Module 10: ReportingEngine

### Objective
Generate all user-facing content: CandidateCards, PresentationContext, approval screen data, Paper Run status card, monthly reports, re-evaluation notifications, and Markdown export.

### Why it matters
This is the only module the user directly experiences. Every other module's work is invisible. If ReportingEngine produces confusing, misleading, or incomplete output, the entire pipeline's value is lost. It must compress complex internal state into plain-language, decision-ready formats.

### Inputs
| Input | Source |
|-------|--------|
| Recommendation | PersistenceStore |
| Candidate[] (surviving) | PersistenceStore |
| Audit[] | PersistenceStore |
| TestResult[] | PersistenceStore |
| PaperRunState | PersistenceStore |
| MonthlyReport data | ExecutionLayer |

### Outputs
| Output | Schema Object | Destination |
|--------|--------------|-------------|
| CandidateCard[] | internal_schema §9 | User (presentation screen) |
| PresentationContext | internal_schema §10 | User (presentation screen) |
| Approval screen data | Derived from Approval schema | User (approval screen) |
| Status card data | Derived from PaperRunState | User (status screen) |
| MonthlyReport | internal_schema §13 | User (push + email) |
| Markdown export | String | User (download) |

### Internal logic

```python
def generate_candidate_cards(recommendation, candidates, audits, test_results) -> list[CandidateCard]:
    cards = []
    for label, cid in [("primary", recommendation.best_candidate_id),
                        ("alternative", recommendation.runner_up_candidate_id)]:
        if cid is None:
            continue
        candidate = get_candidate(candidates, cid)
        audit = get_audit(audits, cid)
        results = get_test_results(test_results, cid)

        card = CandidateCard(
            candidate_id=cid,
            label=label,
            display_name=generate_display_name(candidate),  # No jargon
            summary=simplify_summary(candidate.summary),     # Max 2 sentences, plain language
            strategy_approach=one_sentence_approach(candidate),
            expected_return_band=calculate_return_band(results, candidate),
            estimated_max_loss=calculate_max_loss_band(results, candidate),
            confidence_level=recommendation.confidence_label,
            confidence_reason=recommendation.confidence_explanation[:100],  # 1 sentence
            key_risks=translate_risks(audit.residual_risks[:3]),  # Top 3, plain language
            stop_conditions_headline=format_stop_headline(recommendation)
        )

        # Validate: all fields non-null, non-empty
        validate_card_completeness(card)
        cards.append(card)

    return cards


def generate_monthly_report(paper_run: PaperRunState, benchmark_data) -> MonthlyReport:
    numbers = calculate_monthly_numbers(paper_run, benchmark_data)
    safety = assess_stop_condition_proximity(paper_run)

    summary = generate_natural_language_summary(
        numbers=numbers,
        safety=safety,
        template="monthly_report"
    )
    # LLM generates 3–5 sentence summary in plain Japanese
    # No jargon. No metrics the user needs to interpret.

    return MonthlyReport(
        report_id=generate_uuid(),
        paper_run_id=paper_run.paper_run_id,
        period=current_month_period(),
        summary=summary,
        numbers=numbers,
        safety_note=format_safety_note(safety),
        next=determine_next_actions(paper_run)
    )
```

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| LLM (Claude API) | External | Natural language summary generation, risk translation |
| Term translation table | Internal (static) | Internal terms → user-facing Japanese (40+ terms) |
| PersistenceStore | Internal | Read all objects |
| NotificationService | Internal | Push monthly reports and alerts |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| LLM generates summary with jargon | Medium | Post-process: scan for forbidden terms (Sharpe, drawdown, etc.) and replace with plain equivalents |
| Card validation fails (missing field) | High | Block presentation. Return error to pipeline orchestrator |
| Monthly report generation delayed >3 days | Medium | Send "report delayed" notification. Generate when ready |
| Markdown export template mismatch | Low | Fall back to minimal template (title + summary + risks) |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `reporting.card_generation_latency_ms` | User wait time component |
| `reporting.jargon_replacement_count` | How often LLM uses forbidden terms |
| `reporting.monthly_report_timeliness` | SLA compliance (within 3 days of month end) |
| `reporting.notification_delivery_success` | Notification reliability |

### v1 implementation scope
- CandidateCard generation (2 cards or 1 or 0)
- PresentationContext generation
- Approval screen data formatting
- Paper Run status card
- Monthly natural-language report
- Re-evaluation result notification
- Markdown export

### Later expansion
- v1.5: PDF export
- v1.5: Detail mode (charts, tables, per-test breakdowns)
- v2: Interactive report with drill-down

---

## Module 11: PersistenceStore

### Objective
Store and retrieve all objects across the pipeline lifecycle. Maintain referential integrity. Provide audit trail for every decision.

### Why it matters
Every module reads from and writes to PersistenceStore. It is the backbone that enables the pipeline to be stateful (Paper Run runs for months), traceable (every rejection has a documented reason), and recoverable (partial failures can resume from last good state).

### Inputs
All objects from all modules.

### Outputs
All objects to all modules.

### Internal logic

```python
class PersistenceStore:
    """
    v1: File-based storage. Each run is a directory.
    Structure:
        /data/runs/{run_id}/
            user_intent.json
            domain_frame.json
            research_spec.json
            candidates/
                {candidate_id}.json
            evidence_plans/
                {candidate_id}.json
            validation_plans/
                {candidate_id}.json
            test_results/
                {test_result_id}.json
            data_quality/
                {evidence_item_id}.json
            comparison_result.json
            audits/
                {candidate_id}.json
            recommendation.json
            candidate_cards/
                {candidate_id}.json
            presentation_context.json
            approval.json
        /data/paper_runs/{paper_run_id}/
            state.json                    # Current PaperRunState
            snapshots/
                {date}.json               # Daily snapshots
            reports/
                {report_id}.json          # Monthly reports
            re_evaluations/
                {re_evaluation_id}.json
            signal_history/
                {date}.json               # 90-day rolling
        /data/evidence/
            {run_id}/
                {evidence_item_id}.parquet  # Actual data files
    """

    def save(self, object_type: str, object_id: str, data: dict):
        path = self._resolve_path(object_type, object_id)
        validate_schema(object_type, data)
        write_json(path, data)
        log_write(object_type, object_id)

    def load(self, object_type: str, object_id: str) -> dict:
        path = self._resolve_path(object_type, object_id)
        data = read_json(path)
        validate_schema(object_type, data)
        return data

    def validate_referential_integrity(self, run_id: str):
        """
        Cross-object integrity checks:
        - Every candidate_id in EvidencePlan exists in Candidate[]
        - Every candidate_id in ValidationPlan exists in Candidate[]
        - Every candidate_id in Audit exists in Candidate[]
        - Every item_id in ValidationPlan.required_evidence_items exists in EvidencePlan
        - Recommendation.best_candidate_id has Audit status ∈ {passed, passed_with_warnings}
        - Recommendation.best_candidate_id ≠ runner_up_candidate_id
        - comparison_matrix includes baseline candidate
        """
        # ... implementation
```

### Dependencies
| Dependency | Type | Purpose |
|-----------|------|---------|
| File system | Infrastructure | JSON + Parquet storage |
| JSON schema validator | Internal | Ensure written objects match internal_schema.md |

### Failure modes
| Failure | Severity | Handling |
|---------|----------|---------|
| Disk full | Critical | Halt pipeline, alert operator |
| Schema validation failure on write | High | Reject write, log the invalid object for debugging |
| Referential integrity violation | High | Reject the violating write, log the inconsistency |
| File corruption | Medium | Each write creates a backup. Recover from backup on read failure |
| Concurrent write conflict (Paper Run) | Low | File-level locking. v1 runs single Paper Run per user |

### Observability / logging
| Metric | Purpose |
|--------|---------|
| `persistence.writes_per_run` | Storage growth tracking |
| `persistence.schema_validation_failures` | Bug detection |
| `persistence.referential_integrity_failures` | Pipeline consistency monitoring |
| `persistence.storage_size_bytes` per run | Capacity planning |
| `persistence.paper_run_snapshot_count` | Paper Run health |

### v1 implementation scope
- File-based JSON + Parquet storage
- Schema validation on every write
- Referential integrity checks on pipeline completion
- Daily backup for Paper Run state
- 90-day rolling retention for signal history

### Later expansion
- v1.5: Database migration (PostgreSQL or similar) for multi-user support
- v1.5: API access to stored objects
- v2: Multi-tenant storage with access controls
- v2: Long-term analytics across multiple runs

---

## Cross-cutting Concerns

### Pipeline Orchestrator

Not a module but a coordinator that sequences module execution:

```python
def run_pipeline(raw_input) -> PresentationResult:
    # Phase 1: Planning
    intent = GoalIntake.process(raw_input)
    frame = DomainFramer.frame(intent)
    spec = ResearchSpecCompiler.compile(intent, frame)
    candidates = CandidateGenerator.generate(spec, frame)

    # Phase 2: Evidence + Execution
    evidence_plans = [EvidencePlanner.plan(spec, c) for c in candidates]
    validation_plans = [ValidationPlanner.plan(spec, c, e) for c, e in zip(candidates, evidence_plans)]
    test_results, comparison = ExecutionLayer.execute_validation(validation_plans, evidence_plans)

    # Phase 3: Audit + Recommendation
    audits = [AuditEngine.audit(c, e, v, test_results, comparison, spec)
              for c, e, v in zip(candidates, evidence_plans, validation_plans)]

    # Phase 3a: All-rejection loop (max 1 retry)
    if all(a.audit_status == "rejected" for a in audits):
        rejection_constraints = extract_rejection_constraints(audits)
        candidates = CandidateGenerator.generate(spec, frame, rejection_constraints)
        # Re-run evidence, validation, audit for new candidates
        evidence_plans = [EvidencePlanner.plan(spec, c) for c in candidates]
        validation_plans = [ValidationPlanner.plan(spec, c, e) for c, e in zip(candidates, evidence_plans)]
        test_results, comparison = ExecutionLayer.execute_validation(validation_plans, evidence_plans)
        audits = [AuditEngine.audit(c, e, v, test_results, comparison, spec)
                  for c, e, v in zip(candidates, evidence_plans, validation_plans)]

    # Phase 4: Recommendation + Presentation
    recommendation = RecommendationEngine.generate(audits, candidates, comparison, spec, evidence_plans)
    cards = ReportingEngine.generate_candidate_cards(recommendation, candidates, audits, test_results)
    context = ReportingEngine.generate_presentation_context(recommendation, candidates, audits)

    return PresentationResult(cards=cards, context=context, recommendation=recommendation)
```

### Error propagation

Every module returns a result or raises a typed exception. The orchestrator catches exceptions and decides whether to retry, fall back, or present partial results:

| Exception type | Orchestrator behavior |
|---------------|----------------------|
| `DomainOutOfScopeError` | Stop pipeline. Return domain-out-of-scope message to user |
| `DataAcquisitionError` | Continue with available data. Reduce confidence. Add caveats |
| `BacktestTimeoutError` | Use partial results. Mark tests as partial |
| `AllCandidatesRejectedError` | Retry once (re-generation loop). If still all rejected, present 0-card result |
| `SchemaValidationError` | Stop pipeline. Log for debugging. Return generic error to user |
| `ExternalServiceError` (LLM, API) | Retry 3 times with backoff. If all fail, fall back to template-based output |

### Timeout budget

Total pipeline execution should complete in ≤ 10 minutes:

| Phase | Budget | Modules |
|-------|--------|---------|
| Planning | ≤ 60s | GoalIntake + DomainFramer + ResearchSpecCompiler + CandidateGenerator + EvidencePlanner + ValidationPlanner |
| Data acquisition | ≤ 300s | ExecutionLayer (acquisition only) |
| Validation execution | ≤ 300s | ExecutionLayer (backtests + tests + comparison) |
| Audit + Recommendation | ≤ 30s | AuditEngine + RecommendationEngine |
| Reporting | ≤ 10s | ReportingEngine |
| **Total** | **≤ 700s** | — |

If any phase exceeds its budget, the orchestrator proceeds with partial results.

---

**Role of this document**: This is the implementation blueprint for Give Me a DAY v1. Each module section defines what to build, what it takes in, what it produces, how it fails, and what to measure. Implementation should follow this design module by module, validating each module's outputs against internal_schema.md before proceeding to the next. If implementation reveals a design flaw, update this document before changing the code.

---

**Fixes applied in this version**:
- Module Map: [4] → CandidateGenerator, [5] → EvidencePlanner (was reversed). Now matches core_loop.md Step 4 = Candidate Generation, Step 5 = Evidence Planning (I-1)
- Module section headings renumbered accordingly: "Module 4: CandidateGenerator", "Module 5: EvidencePlanner" (I-1)
- Reject loop target updated: `reject? → [4]` (CandidateGenerator) instead of `[5]` (I-1)
