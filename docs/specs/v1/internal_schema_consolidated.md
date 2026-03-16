# Internal Schema — v1 Consolidated

**Document type**: Single source of truth for all internal data structures
**Domain**: Investment research / Strategy validation / Hypothesis-testing pipelines
**Version**: v1 consolidated
**Status**: Design-complete — ready for implementation review
**Incorporates**: v1_core_loop_spec.md, v1_output_package_spec.md, v1_audit_rubric_spec.md, v1_evidence_taxonomy_spec.md

---

## Schema Principle

This schema models:
- intent（何を達成したいか）
- framing（どう検証問題に変換したか）
- candidates（どの方向性を検討したか）
- evidence（何のデータで検証するか）
- validation（どうテストするか）
- audit（何が問題か）
- rejection（何を棄却したか、なぜか）
- recommendation（何を条件付きで推奨するか）
- re-evaluation（いつ推奨が無効になるか）

NOT just requirements and architecture.

---

## Object Relationship Map

```
UserIntent ──→ DomainFrame ──→ ResearchSpec
                                    │
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
               Candidate[]    EvidencePlan[]   (shared constraints)
                    │               │
                    ↓               ↓
              ValidationPlan[] ←────┘
                    │
                    ↓
                Audit[] ──→ (compound check) ──→ Recommendation
                                                      │
                                                      ↓
                                              ReEvaluationTriggerSet
```

All objects share `run_id` as the top-level correlation key.
One run produces exactly one of each top-level object, except:
- Candidate[]: 3–5 per run
- EvidencePlan[]: 1 per Candidate
- ValidationPlan[]: 1 per Candidate
- Audit[]: 1 per Candidate

---

## 1. UserIntent

**Produced by**: Core Loop Step 1 (Goal Intake)
**Consumed by**: Step 2 (Domain Framing), Step 3 (Research Spec)

```jsonc
{
  // === Identity ===
  "run_id": "string",                    // UUID. Top-level correlation key for the entire run
  "created_at": "ISO-8601",

  // === Raw input ===
  "raw_goal": "string",                  // User's original text, verbatim

  // === Structured interpretation ===
  "domain": "investment_research",        // v1: hardcoded. Other values rejected at intake
  "user_goal_summary": "string",          // System's structured interpretation of the goal
  "success_definition": "string",         // Must contain: what, how much, over what period
                                          // Vague definitions ("make profit") are rejected

  // === Preferences ===
  "risk_preference": "very_low | low | medium | high",
  "time_horizon_preference": "fast | one_day | one_week | one_month | quality_over_speed",
  "automation_preference": "advice_only | research_assist | semi_automated | full_if_safe",

  // === Constraints ===
  "must_not_do": ["string"],             // Explicit prohibitions. Actively elicited via domain checklist
  "available_inputs": ["string"],         // Data/tools user already has access to

  // === Uncertainty ===
  "open_uncertainties": ["string"]        // Items that could not be resolved during intake
                                          // If empty, Step 3 must log justification
}
```

### Validation rules
- `domain` must be `"investment_research"` in v1. All other values → reject with out-of-scope message.
- `success_definition` must not be a single vague sentence. Minimum: target metric + magnitude + timeframe.
- `open_uncertainties` may be empty, but if so, a log entry is required at Step 3 explaining why.
- `must_not_do` is populated both from user input and from a domain-specific prohibition checklist (leverage, asset class exclusions, short-selling restrictions, etc.).

---

## 2. DomainFrame

**Produced by**: Core Loop Step 2 (Domain Framing)
**Consumed by**: Step 3 (Research Spec), Step 4 (Candidate Generation)
**New in consolidated schema** — did not exist in original internal_schema.md.

```jsonc
{
  // === Identity ===
  "run_id": "string",

  // === Problem reframing ===
  "reframed_problem": "string",          // Must be in the form: "Is X testable under conditions Y?"
                                          // Converts "I want to build..." into "Can we validate..."
  "core_hypothesis": "string",            // Single-sentence central hypothesis

  // === Testable decomposition ===
  "testable_claims": [
    {
      "claim_id": "string",
      "claim": "string",                  // A verifiable assertion
      "falsification_condition": "string"  // What data/result would disprove this claim
                                           // REQUIRED. Claims without falsification conditions are invalid
    }
  ],

  // === Assumptions and context ===
  "critical_assumptions": ["string"],     // Assumptions this framing depends on
  "regime_dependencies": ["string"],      // Which market regimes are assumed. MUST NOT be empty
  "comparable_known_approaches": [
    {
      "name": "string",
      "relevance": "string",
      "known_outcome": "string"           // What is already known about this approach
    }
  ]
}
```

### Validation rules
- `reframed_problem` must contain a testability clause ("Is ... testable/verifiable/validatable under ...").
- `testable_claims[].falsification_condition` is required. A claim without a falsification condition is not a claim.
- `regime_dependencies` must not be empty. If user did not specify, Step 2 must actively identify at least one regime assumption.
- User confirmation checkpoint occurs after this object is produced.

---

## 3. ResearchSpec

**Produced by**: Core Loop Step 3 (Research Spec Compilation)
**Consumed by**: Step 4, 5, 6, 7, 8

```jsonc
{
  // === Identity ===
  "spec_id": "string",
  "run_id": "string",

  // === Objectives ===
  "primary_objective": "string",          // Exactly one
  "secondary_objectives": ["string"],     // Max 3

  // === Framing ===
  "problem_frame": "string",             // Copied from DomainFrame.reframed_problem

  // === Assumptions (structured — expanded from original) ===
  "assumption_space": [
    {
      "assumption_id": "string",
      "statement": "string",
      "source": "user_stated | system_inferred | domain_default",
      "fragility": "low | medium | high",  // How sensitive is the analysis if this breaks
      "falsification_trigger": "string"     // What would invalidate this assumption
    }
  ],                                       // Max 15 items. Shared across all candidates
                                           // Candidate-specific assumptions go in Candidate.core_assumptions

  // === Constraints ===
  "constraints": {
    "time": "string",
    "budget": "string",
    "tooling": ["string"],
    "forbidden_behaviors": ["string"]      // From UserIntent.must_not_do + domain defaults
  },

  // === Evidence requirements ===
  "evidence_requirements": {
    "required_data": ["string"],           // Category-level descriptions (e.g., "daily OHLCV for Japan equities")
    "optional_data": ["string"],
    "proxy_data_allowed": true,            // Global flag. Per-item proxy decisions in EvidencePlan
    "evidence_gaps": ["string"]            // Known gaps at spec time. Detailed in EvidencePlan
  },

  // === Validation requirements (structured — expanded from original) ===
  "validation_requirements": {
    "must_test": ["string"],
    "must_compare": ["string"],
    "disqualifying_failures": [
      {
        "failure_id": "string",
        "description": "string",           // e.g., "Post-cost Sharpe < 0.3"
        "metric": "string",
        "threshold": "string",
        "applies_to": "all_candidates | specific_candidate_types"
      }
    ],
    "minimum_evidence_standard": "weak | moderate | strong"
                                           // Derived mechanically:
                                           //   very_low risk → strong
                                           //   low + quality_over_speed → strong
                                           //   medium → moderate
                                           //   high + fast → weak (with warning)
                                           //   default → moderate
  },

  // === Recommendation requirements (v1: all true, hardcoded, not user-configurable) ===
  "recommendation_requirements": {
    "must_return_runner_up": true,
    "must_return_rejections": true,
    "must_surface_unknowns": true,
    "allow_no_valid_candidate": true
  }
}
```

### Validation rules
- `primary_objective` is exactly 1.
- `secondary_objectives` max 3.
- `assumption_space` max 15. Each item must have `falsification_trigger`.
- `disqualifying_failures` must contain at least one item.
- `recommendation_requirements` fields are all `true` in v1. Not user-configurable.

### Changes from original
- `assumption_space`: `["string"]` → structured array with `assumption_id`, `source`, `fragility`, `falsification_trigger`.
- `disqualifying_failures`: `["string"]` → structured array with `failure_id`, `metric`, `threshold`, `applies_to`.

---

## 4. Candidate

**Produced by**: Core Loop Step 4 (Candidate Generation)
**Consumed by**: Step 5, 6, 7, 8

```jsonc
{
  // === Identity ===
  "candidate_id": "string",              // Format: {run_id}-C{sequence}. Immutable after creation
  "run_id": "string",
  "generation_round": 1,                 // 1 = initial, 2 = regenerated after full rejection (NEW)

  // === Classification ===
  "name": "string",
  "candidate_type": "baseline | conservative | exploratory | hybrid",

  // === Description ===
  "summary": "string",
  "architecture_outline": ["string"],     // Conceptual pipeline steps, not implementation code

  // === Assumptions (candidate-specific — expanded from original) ===
  "core_assumptions": [
    {
      "assumption_id": "string",
      "statement": "string",
      "impact_if_false": "string"         // REQUIRED. How the candidate breaks if this is false
    }
  ],                                      // No duplication with ResearchSpec.assumption_space

  // === Requirements ===
  "required_inputs": ["string"],

  // === Assessments ===
  "validation_burden": "low | medium | high",
  "implementation_complexity": "low | medium | high",
  "expected_strengths": ["string"],
  "expected_weaknesses": ["string"],
  "known_risks": ["string"]              // Must not be empty
}
```

### Validation rules
- Min 3, max 5 candidates per run.
- Type distribution: exactly 1 baseline, ≥1 conservative, ≥1 exploratory. Same type ×2 requires >30% architectural divergence.
- `core_assumptions[].impact_if_false` is required.
- `known_risks` must not be empty.
- Candidates are immutable. Rejected candidates are not modified; new ones get new IDs in `generation_round: 2`.
- Max 2 generation rounds per run.

### Changes from original
- Added `generation_round`.
- `core_assumptions`: `["string"]` → structured array with `assumption_id`, `impact_if_false`.

---

## 5. EvidencePlan

**Produced by**: Core Loop Step 5 (Evidence Planning)
**Consumed by**: Step 6, 7, 8
**New in consolidated schema.**

```jsonc
{
  // === Identity ===
  "evidence_plan_id": "string",
  "candidate_id": "string",              // One EvidencePlan per Candidate
  "run_id": "string",

  // === Evidence items ===
  "evidence_items": [
    {
      "item_id": "string",

      // --- Classification (Evidence Taxonomy) ---
      "category": "price | fundamental | alternative | macro | sentiment | flow | metadata",
      "description": "string",

      // --- Requirement level ---
      "requirement_level": "required | optional | proxy_acceptable",

      // --- Availability ---
      "availability": "available | obtainable_with_effort | unavailable",

      // --- Temporal coverage ---
      "temporal_coverage": {
        "start": "ISO-8601 | null",
        "end": "ISO-8601 | null",
        "frequency": "tick | minute | daily | weekly | monthly | quarterly | annual"
      },

      // --- Quality ---
      "quality_concerns": ["string"],     // From Evidence Taxonomy quality axes

      // --- Bias ---
      "known_biases": ["string"],         // Bias IDs from Evidence Taxonomy (e.g., "PRC-B01", "FND-B02")

      // --- Point-in-time (NEW — driven by Evidence Taxonomy) ---
      "point_in_time_status": "full | partial | none",
                                          // full: all historical vintages preserved
                                          // partial: publication dates available, revision history incomplete
                                          // none: latest values only

      // --- Reporting lag (NEW — driven by Evidence Taxonomy) ---
      "reporting_lag_days": "number | null",
                                          // Days between reference date and publication date
                                          // null = real-time or not applicable

      // --- Leakage risk (NEW — connects Taxonomy to Audit Rubric) ---
      "leakage_risk_patterns": ["string"],
                                          // Audit Rubric LKG pattern IDs (e.g., ["LKG-01", "LKG-06"])
                                          // Pre-populated based on category + pit_status + lag

      // --- Proxy ---
      "proxy_option": {
        "description": "string | null",
        "quality_loss_estimate": "minimal | medium | severe",
        "permitted": true,                // Based on Evidence Taxonomy proxy rules
        "prohibition_reason": "string | null"
      }
    }
  ],

  // === Gap assessment ===
  "critical_gaps": [
    {
      "gap_id": "string",
      "description": "string",
      "severity": "manageable | blocking",
      "affected_evidence_items": ["string"],
      "impact_on_recommendation": "string",
      "mitigation_option": "string | null"
    }
  ],

  // === Aggregate status ===
  "gap_severity": "none | manageable | blocking",
                                          // none: all required available
                                          // manageable: obtainable or proxy-able
                                          // blocking: required + unavailable + no proxy

  // === Coverage metrics ===
  "coverage": {
    "required_total": "number",
    "required_available": "number",
    "required_obtainable": "number",
    "required_unavailable": "number",
    "coverage_percentage": "number"       // required_available / required_total × 100
  },

  "notes": "string | null"
}
```

### Validation rules
- One EvidencePlan per Candidate.
- `known_biases` must reference valid Taxonomy bias IDs.
- `leakage_risk_patterns` must reference valid Audit Rubric LKG IDs.
- If `point_in_time_status: "none"` for FND/MAC/SNT items → `leakage_risk_patterns` must include `"LKG-07"`.
- If `reporting_lag_days: null` for FND/MAC/FLW items → log quality_concern.
- `gap_severity: blocking` → triggers Audit EVD-01.
- `coverage.coverage_percentage` feeds into confidence_label calculation (FC-02).

---

## 6. ValidationPlan

**Produced by**: Core Loop Step 6 (Validation Plan Generation)
**Consumed by**: Step 7, 8

```jsonc
{
  // === Identity ===
  "validation_plan_id": "string",
  "candidate_id": "string",              // One ValidationPlan per Candidate
  "run_id": "string",

  // === Test sequence (ordered) ===
  "test_sequence": [
    {
      "test_id": "string",
      "test_type": "offline_backtest | walk_forward | out_of_sample | regime_split | stress_test | sensitivity | paper_run | monte_carlo",
      "description": "string",
      "purpose": "string",                // Why this test is needed (NEW)

      // --- Data requirements ---
      "required_evidence_items": ["string"],  // item_id refs from EvidencePlan

      // --- Metrics ---
      "metrics": [
        {
          "metric_id": "string",
          "name": "string",
          "calculation_method": "string",
          "pass_threshold": "string",
          "fail_threshold": "string",     // Maps to ResearchSpec.disqualifying_failures
          "comparison_target": "null | baseline_candidate | benchmark | absolute_value"
        }
      ],

      // --- Time windows (structured — expanded from original) ---
      "time_windows": [
        {
          "label": "string",
          "start": "ISO-8601",
          "end": "ISO-8601",
          "rationale": "string"           // REQUIRED. Prevents cherry-picking (Audit OVF-02)
        }
      ],

      // --- Failure conditions ---
      "failure_conditions": ["string"],   // Min 1. A test without failure conditions is not a test

      // --- Dependencies (NEW) ---
      "execution_prerequisites": ["string"],  // test_ids that must pass first
      "estimated_effort": "low | medium | high"
    }
  ],

  // === Plan completeness (derived from EvidencePlan.gap_severity) ===
  "plan_completeness": "complete | partial_due_to_evidence_gaps | minimal",

  // === Comparison matrix ===
  "comparison_matrix": {
    "candidates_compared": ["string"],    // Must include baseline
    "comparison_metrics": ["string"],
    "comparison_method": "string"
  },

  "notes": "string | null"
}
```

### Validation rules
- One ValidationPlan per Candidate.
- `failure_conditions` must not be empty per test.
- `time_windows[].rationale` must not be empty per window.
- `comparison_matrix.candidates_compared` must include baseline.
- `plan_completeness` is derived from `EvidencePlan.gap_severity`.
- Out-of-sample period ≥ 1/3 of in-sample. Below → Audit flag.

### Changes from original
- `test_types` flat list → structured `test_sequence` with per-test detail.
- Added `purpose`, `time_windows.rationale`, `execution_prerequisites`, `estimated_effort`.
- Added `plan_completeness`.
- `metrics` expanded with `metric_id`, `calculation_method`, `comparison_target`.
- `required_data_sources` → `required_evidence_items` (reference EvidencePlan).
- Test type enum: 5 → 8 values (added `out_of_sample`, `regime_split`, `sensitivity`).

---

## 7. Audit

**Produced by**: Core Loop Step 7 (Audit / Rejection)
**Consumed by**: Step 8

```jsonc
{
  // === Identity ===
  "candidate_id": "string",
  "run_id": "string",

  // === Status (NEW — derived) ===
  "audit_status": "passed | passed_with_warnings | rejected",
                                          // any(disqualifying) → rejected
                                          // count(high) ≥ 3 → passed_with_warnings
                                          // any(critical AND mitigation != null) → passed_with_warnings
                                          // else → passed

  // === Issues ===
  "issues": [
    {
      "issue_id": "string",              // Pattern ID from Rubric (e.g., "LKG-01")

      "severity": "low | medium | high | critical",

      "category": "assumption | evidence_gap | leakage_risk | overfitting_risk | realism | regime_dependency | complexity | observability | cost_assumption | recommendation_risk",
                                          // 10 categories (expanded from original 7)

      "title": "string",
      "explanation": "string",            // Min 2 sentences. Disqualifying: min 3

      "mitigation": "string | null",      // Specific. "More testing" is insufficient
      "disqualifying": false,

      // === Traceability (NEW) ===
      "related_evidence_items": ["string"],
      "related_assumptions": ["string"],
      "related_tests": ["string"]
    }
  ],

  // === Rejection ===
  "rejection_reason": "string | null",    // Min 3 sentences if rejected:
                                          // what is wrong → why fatal → whether fixable

  // === Surviving state (NEW — for passed candidates) ===
  "surviving_assumptions": ["string"],    // Must not be empty (FC-05)
  "residual_risks": ["string"],

  // === Compound patterns (NEW — Rubric Appendix C) ===
  "compound_patterns": [
    {
      "pattern_name": "string",
      "constituent_issues": ["string"],   // issue_ids
      "compound_severity": "string",
      "disqualifying": false
    }
  ],

  // === Meta-audit (NEW — FC-01) ===
  "meta_audit": {
    "total_issues": "number",
    "zero_issue_warning": false,
    "rescan_performed": false,
    "rescan_categories": ["string"]
  }
}
```

### Validation rules
- `audit_status` is derived, not manually set.
- `explanation` min 2 sentences; disqualifying min 3.
- `mitigation` must be specific with data/tests/thresholds. Generic → invalid.
- `surviving_assumptions` must not be empty for passed candidates (FC-05).
- `rejection_reason` required and min 3 sentences when `audit_status: rejected`.
- If `meta_audit.total_issues == 0` → `zero_issue_warning: true` + `rescan_performed: true`.
- Compound patterns evaluated after all individual issues (Phase 4).

### Changes from original
- Added `audit_status`.
- `category` enum: 7 → 10 (added `overfitting_risk`, `regime_dependency`, `cost_assumption`).
- Added `surviving_assumptions`, `residual_risks`.
- Added `compound_patterns`.
- Added `meta_audit`.
- Added traceability fields per issue.

---

## 8. Recommendation

**Produced by**: Core Loop Step 8 (Conditional Recommendation)
**Consumed by**: Step 9, Output Package

```jsonc
{
  // === Identity ===
  "run_id": "string",

  // === Selection ===
  "best_candidate_id": "string | null",   // null = no valid candidate (valid output)
  "runner_up_candidate_id": "string | null",
  "rejected_candidate_ids": ["string"],

  // === Ranking rationale ===
  "ranking_logic": ["string"],            // Min 3. Per-axis comparison. "Overall good" PROHIBITED (FC-03)

  // === Conditions (structured — expanded from original) ===
  "critical_conditions": [
    {
      "condition_id": "string",
      "statement": "string",              // "If X, this recommendation is invalid"
      "source": "string",                 // Which surviving_assumption generated this
      "verification_method": "string",
      "verification_timing": "string"
    }
  ],                                      // MUST NOT be empty

  // === Unknowns (structured — expanded from original) ===
  "open_unknowns": [
    {
      "unknown_id": "string",
      "description": "string",
      "impact_if_resolved_positively": "string",
      "impact_if_resolved_negatively": "string",
      "resolution_method": "string"
    }
  ],                                      // MUST NOT be empty

  // === Confidence ===
  "confidence_label": "low | medium | high",
                                          // Mechanical derivation (FC-02):
                                          //   evidence_coverage < 50% → low
                                          //   critical(mitigated) ≥ 2 → low
                                          //   high ≥ 3 → low
                                          //   coverage < 80% AND high ≥ 1 → low
                                          //   coverage ≥ 80% AND high=0 AND critical=0 → medium
                                          //   coverage=100% AND all ≤ medium AND plan=complete → medium
                                          //   high: rare in v1
                                          // Manual override PROHIBITED
  "confidence_explanation": "string",     // Min 3 sentences

  // === Recommendation expiry (NEW) ===
  "recommendation_expiry": {
    "type": "time_based | event_based | evidence_based",
    "description": "string",
    "expiry_date": "ISO-8601 | null"      // For time_based only
  },                                      // REQUIRED. No null allowed

  // === Monitoring ===
  "monitoring_or_recheck_rules": ["string"],

  // === Next steps (structured — expanded from original) ===
  "next_validation_steps": [
    {
      "step_id": "string",
      "description": "string",
      "who": "string",                    // user | system | external
      "data_required": "string",
      "test_type": "string",
      "success_threshold": "string",
      "priority": "critical | high | medium"
    }
  ]                                       // Each must have who + data + test + threshold
}
```

### Validation rules
- `critical_conditions` must not be empty.
- `open_unknowns` must not be empty.
- `ranking_logic` min 3 items with specific comparison axes.
- `confidence_label` mechanically derived. No override.
- `recommendation_expiry` required. Null not allowed.
- `next_validation_steps` each must have all 4 elements.
- `open_unknowns` count > 5 → force `confidence_label: low`.
- If `best_candidate_id: null`, `ranking_logic` + `open_unknowns` + `next_validation_steps` still required.

### Changes from original
- `critical_conditions`: `["string"]` → structured with `verification_method`, `verification_timing`.
- `open_unknowns`: `["string"]` → structured with impact analysis, `resolution_method`.
- Added `recommendation_expiry`.
- `next_validation_steps`: `["string"]` → structured with `who`, `data_required`, `test_type`, `success_threshold`.

---

## 9. ReEvaluationTriggerSet

**Produced by**: Core Loop Step 9 (Re-evaluation Trigger)
**Consumed by**: Output Package
**New in consolidated schema.**

```jsonc
{
  // === Identity ===
  "run_id": "string",

  // === Triggers ===
  "triggers": [
    {
      "trigger_id": "string",
      "trigger_type": "time_based | data_based | market_event | assumption_invalidation | performance_degradation",
      "description": "string",
      "detection_method": "string",        // Specific: indicator, threshold, source
      "urgency": "routine | elevated | immediate",
      "affected_elements": ["string"],
      "recommended_action": "rerun_full_loop | rerun_from_step_N | update_evidence_only | manual_review"
    }
  ],                                       // Max 10. Sorted by urgency

  // === Default schedule ===
  "default_recheck_interval": "string",    // Derived from time_horizon_preference

  // === Coverage ===
  "assumption_trigger_coverage": {
    "total_assumptions": "number",
    "assumptions_with_triggers": "number",
    "uncovered_assumptions": ["string"]
  },

  "notes": "string | null"
}
```

### Validation rules
- Max 10 triggers.
- `detection_method` must reference specific indicators and thresholds.
- Each assumption in `ResearchSpec.assumption_space` should have ≥1 trigger. Uncovered → warning.

---

## Changelog Summary

### New objects added

| Object | Source document | Reason |
|--------|---------------|--------|
| DomainFrame | Core Loop spec | Step 2 produces distinct output. Previously implicit |
| EvidencePlan | Evidence Taxonomy spec | Per-item quality/bias/leakage tracking required structured object |
| ReEvaluationTriggerSet | Core Loop spec | Step 9 output. Missing from original schema |

### New fields on existing objects

| Object | New fields | Source |
|--------|-----------|--------|
| ResearchSpec | assumption_space (structured), disqualifying_failures (structured) | Core Loop + Audit Rubric |
| Candidate | generation_round, core_assumptions (structured) | Core Loop + Audit Rubric |
| ValidationPlan | purpose, time_windows.rationale, execution_prerequisites, estimated_effort, plan_completeness | Core Loop + Audit Rubric |
| Audit | audit_status, surviving_assumptions, residual_risks, compound_patterns, meta_audit, issue traceability | Audit Rubric |
| Recommendation | critical_conditions (structured), open_unknowns (structured), recommendation_expiry, next_validation_steps (structured) | Output Package + Core Loop |

### Expanded enums

| Field | Original | Consolidated | Source |
|-------|----------|-------------|--------|
| Audit.category | 7 values | 10 values | Audit Rubric (+overfitting_risk, regime_dependency, cost_assumption) |
| EvidencePlan.category | (new) | 7 values | Evidence Taxonomy |
| ValidationPlan.test_type | 5 values | 8 values | Core Loop (+out_of_sample, regime_split, sensitivity) |

---

## Cross-object Invariants

| # | Invariant | Enforcement |
|---|-----------|-------------|
| 1 | Every Candidate has exactly 1 EvidencePlan + 1 ValidationPlan + 1 Audit | Foreign key on candidate_id |
| 2 | Only passed/passed_with_warnings candidates can be best/runner_up | Runtime |
| 3 | best_candidate_id ≠ runner_up_candidate_id | Schema |
| 4 | rejected_candidate_ids = all where audit_status=rejected | Derived |
| 5 | Recommendation.critical_conditions derived from best candidate's Audit.surviving_assumptions | Runtime |
| 6 | Recommendation.open_unknowns includes best candidate's EvidencePlan.critical_gaps | Runtime |
| 7 | confidence_label is mechanically derived (FC-02). No override field exists | Schema |
| 8 | ValidationPlan.comparison_matrix must include baseline | Runtime |
| 9 | critical_conditions must not be empty | Schema |
| 10 | open_unknowns must not be empty | Schema |
| 11 | recommendation_expiry must not be null | Schema |
| 12 | ReEvaluationTriggerSet should cover all assumption_space items | Warning |
| 13 | Max 2 generation_rounds. Round 2 full rejection → best_candidate_id=null | Runtime |

---

## v1 Deferred Fields

Fields defined in schema but not fully implemented in v1:

| Object.Field | v1 behavior | Full implementation |
|-------------|-------------|-------------------|
| EvidencePlan.temporal_coverage (precise dates) | Approximate ranges accepted | v1.5 (data source integration) |
| ValidationPlan.estimated_effort (automated) | Manual estimation | v1.5 (benchmarks needed) |
| ReEvaluationTriggerSet.detection_method (automated) | Definition only | v1.5 (live data feeds) |
| Recommendation.next_validation_steps.who="system" | User-executed only | v1.5 (auto-execution) |
| Audit severity adjustment from results | Plan-based severity only | v1.5 (backtest feedback) |

## Fields NOT in v1 Schema

| Field | Reason |
|-------|--------|
| implementation_code | Code generation is not the product center |
| performance_prediction | False confidence. Prohibited without evidence |
| cost_estimate_usd | Unreliable at planning stage |
| regulatory_compliance | Legal advice out of scope |

---

## Implementation Notes

### ID generation
- `run_id`: UUID v4
- `candidate_id`: `{run_id}-C{1..5}`
- `evidence_plan_id`: `{run_id}-EP-{candidate_sequence}`
- `validation_plan_id`: `{run_id}-VP-{candidate_sequence}`
- Other IDs: UUID v4 or sequential within parent

### Serialization
- All objects JSON-serializable
- All dates ISO-8601
- All enums lowercase strings
- Null permitted only where explicitly marked `"type | null"`

### Storage
- v1: file-based (JSON per run). No database required
- One run = one directory with all objects
- Write-once except Recommendation and ReEvaluationTriggerSet (written last)

### Observability
- Log creation timestamp per object
- Log Audit execution time per candidate
- Log confidence_label derivation inputs for calibration
- Log FC-01 rescan events as system events
