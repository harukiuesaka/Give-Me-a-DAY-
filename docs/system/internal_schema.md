# Internal Schema

## Schema Principle

This schema models the full product lifecycle:

- **Intent**: what the user wants
- **Framing**: what should be tested
- **Evidence**: what data exists and at what quality
- **Candidates**: what directions were considered
- **Validation**: how candidates were tested
- **Audit**: what weaknesses were found and what was rejected
- **Recommendation**: what survived and under what conditions
- **Approval**: what the user agreed to
- **Runtime**: the operating system and its safety mechanisms
- **Re-evaluation**: when and why to revisit

---

## Object Relationship Map

```
UserIntent
  ↓
DomainFrame
  ↓
ResearchSpec
  ↓
Candidate[] ←──────────── EvidencePlan[] (per candidate)
  ↓                              ↓
ValidationPlan[] ←───────────────┘
  ↓
Audit[] ──→ Recommendation
                ↓
         CandidateCard[] (user-facing, derived)
                ↓
            Approval
                ↓
          PaperRunState
                ↓
          MonthlyReport[]
                ↓
        ReEvaluationResult
```

---

## 1. UserIntent

```jsonc
{
  "run_id": "string",
  "created_at": "ISO-8601",
  "raw_goal": "string",
  "domain": "investment_research",
  "user_goal_summary": "string",
  "success_definition": "string",
  "risk_preference": "very_low | low | medium | high",
  "time_horizon_preference": "fast | one_day | one_week | one_month | quality_over_speed",
  "must_not_do": ["string"],
  "available_inputs": ["string"],
  "open_uncertainties": ["string"]
}
```

Notes:
- `domain` is always `"investment_research"` in v1. Non-investment goals are rejected at intake.
- `success_definition` should contain what, how much, and over what period. If incomplete, gaps go to `open_uncertainties`.
- `automation_preference` has been removed. v1 behavior is fixed: validate → present → approve → Paper Run.

---

## 2. DomainFrame

```jsonc
{
  "run_id": "string",
  "archetype": "FACTOR | STAT_ARB | EVENT | MACRO | ML_SIGNAL | ALT_DATA | HYBRID | UNCLASSIFIED",
  "reframed_problem": "string",
  "core_hypothesis": "string",
  "testable_claims": [
    {
      "claim_id": "string",
      "layer": "premise | core | practical",
      "claim": "string",
      "falsification_condition": "string"
    }
  ],
  "critical_assumptions": ["string"],
  "regime_dependencies": ["string"],
  "comparable_known_approaches": [
    {
      "name": "string",
      "relevance": "string",
      "known_outcome": "string"
    }
  ]
}
```

Notes:
- `archetype` drives claim decomposition patterns and candidate generation templates.
- `testable_claims` must have at least 1 per layer (premise, core, practical). Each must have a `falsification_condition`.
- `regime_dependencies` must be non-empty. All investment strategies depend on regime.

---

## 3. ResearchSpec

```jsonc
{
  "spec_id": "string",
  "run_id": "string",
  "primary_objective": "string",
  "secondary_objectives": ["string"],
  "problem_frame": "string",
  "assumption_space": [
    {
      "assumption_id": "string",
      "statement": "string",
      "category": "market_efficiency | stationarity | liquidity | data_quality | causal | cost | regulatory",
      "falsification_condition": "string",
      "source": "user_stated | system_inferred | domain_default"
    }
  ],
  "constraints": {
    "time": "string",
    "budget": "string",
    "tooling": ["string"],
    "forbidden_behaviors": ["string"]
  },
  "evidence_requirements": {
    "required_data": ["string"],
    "optional_data": ["string"],
    "proxy_data_allowed": true,
    "evidence_gaps": ["string"]
  },
  "validation_requirements": {
    "must_test": ["string"],
    "must_compare": ["string"],
    "disqualifying_failures": [
      {
        "failure_id": "string",
        "description": "string",
        "metric": "string",
        "threshold": "string",
        "applies_to": "all_candidates | specific_candidate_types"
      }
    ],
    "minimum_evidence_standard": "weak | moderate | strong"
  },
  "recommendation_requirements": {
    "must_return_runner_up": true,
    "must_return_rejections": true,
    "must_surface_unknowns": true,
    "allow_no_valid_candidate": true
  }
}
```

Notes:
- `recommendation_requirements` flags are all `true` and hardcoded in v1.
- `minimum_evidence_standard` is mechanically derived from `risk_preference` × `time_horizon_preference`.
- `assumption_space` is max 15 items. Candidate-specific assumptions live in Candidate.core_assumptions.

---

## 4. Candidate

```jsonc
{
  "candidate_id": "string",
  "name": "string",
  "candidate_type": "baseline | conservative | exploratory | hybrid",
  "summary": "string",
  "architecture_outline": ["string"],
  "core_assumptions": [
    {
      "assumption_id": "string",
      "statement": "string",
      "failure_impact": "string"
    }
  ],
  "required_inputs": ["string"],
  "validation_burden": "low | medium | high",
  "implementation_complexity": "low | medium | high",
  "expected_strengths": ["string"],
  "expected_weaknesses": ["string"],
  "known_risks": ["string"]
}
```

Notes:
- Min 3 candidates per run (1 baseline + 1 conservative + 1 exploratory).
- `known_risks` must be non-empty. Candidates that claim zero risks are immature.
- `core_assumptions` are candidate-specific, separate from ResearchSpec.assumption_space.

---

## 5. EvidencePlan

```jsonc
{
  "evidence_plan_id": "string",
  "candidate_id": "string",
  "evidence_items": [
    {
      "item_id": "string",
      "category": "price | fundamental | alternative | macro | sentiment | flow | metadata",
      "description": "string",
      "requirement_level": "required | optional | proxy_acceptable",
      "availability": "available | obtainable_with_effort | unavailable",
      "quality_concerns": ["string"],
      "known_biases": ["string"],
      "temporal_coverage": {
        "start": "ISO-8601",
        "end": "ISO-8601",
        "frequency": "tick | minute | daily | weekly | monthly | quarterly | annual"
      },
      "point_in_time_status": "full | partial | none",
      "reporting_lag_days": "integer | null",
      "proxy_option": {
        "description": "string",
        "quality_loss_estimate": "minimal | medium | severe",
        "permitted": true,
        "prohibition_reason": "string | null"
      },
      "leakage_risk_patterns": ["string"]
    }
  ],
  "critical_gaps": [
    {
      "gap_id": "string",
      "description": "string",
      "affected_evidence_items": ["string"],
      "severity": "manageable | blocking",
      "impact_on_recommendation": "string",
      "mitigation_option": "string | null"
    }
  ],
  "gap_severity": "none | manageable | blocking",
  "coverage_metrics": {
    "required_total": "integer",
    "required_available": "integer",
    "required_obtainable": "integer",
    "required_unavailable": "integer",
    "coverage_percentage": "number"
  }
}
```

Notes:
- `known_biases` references Evidence Taxonomy bias IDs (e.g., "PRC-B01").
- `point_in_time_status: "none"` on FND/MAC/SNT/FLW/MTA categories triggers automatic LKG-07 flag.
- `coverage_metrics` feeds into confidence_label calculation (FC-02).

---

## 6. ValidationPlan

```jsonc
{
  "validation_plan_id": "string",
  "candidate_id": "string",
  "test_sequence": [
    {
      "test_id": "string",
      "test_type": "offline_backtest | walk_forward | out_of_sample | regime_split | stress_test | sensitivity | paper_run | monte_carlo",
      "purpose": "string",
      "method_summary": "string",
      "required_evidence_items": ["string"],
      "metrics": [
        {
          "name": "string",
          "calculation_method": "string",
          "pass_threshold": "string",
          "fail_threshold": "string",
          "comparison_target": "null | baseline_candidate | benchmark | absolute_value"
        }
      ],
      "time_windows": [
        {
          "label": "string",
          "start": "ISO-8601",
          "end": "ISO-8601",
          "selection_rationale": "string"
        }
      ],
      "failure_conditions": ["string"],
      "execution_prerequisites": ["string"],
      "estimated_effort": "low | medium | high"
    }
  ],
  "plan_completeness": "complete | partial_due_to_evidence_gaps | minimal",
  "comparison_matrix": {
    "candidates_compared": ["string"],
    "comparison_metrics": ["string"],
    "comparison_method": "string"
  }
}
```

Notes:
- Every test must have ≥ 1 `failure_conditions`. Tests that cannot fail are not tests.
- `comparison_matrix.candidates_compared` must include the baseline candidate.
- `plan_completeness` derives from EvidencePlan.gap_severity.

---

## 7. Audit

```jsonc
{
  "candidate_id": "string",
  "audit_status": "passed | passed_with_warnings | rejected",
  "issues": [
    {
      "issue_id": "string",
      "severity": "low | medium | high | critical",
      "category": "assumption | evidence_gap | leakage_risk | overfitting_risk | realism | regime_dependency | complexity | observability | cost_assumption | recommendation_risk",
      "title": "string",
      "explanation": "string",
      "mitigation": "string | null",
      "disqualifying": false,
      "affected_evidence_items": ["string"],
      "affected_assumptions": ["string"],
      "compound_pattern": "string | null"
    }
  ],
  "rejection_reason": "string | null",
  "surviving_assumptions": ["string"],
  "residual_risks": ["string"],
  "meta_audit": {
    "total_issues": "integer",
    "issues_by_severity": { "critical": 0, "high": 0, "medium": 0, "low": 0 },
    "zero_issue_flag": false,
    "compound_patterns_detected": ["string"]
  }
}
```

Notes:
- `audit_status` determination: any disqualifying issue → rejected; ≥3 high → passed_with_warnings; critical with mitigation → passed_with_warnings; else → passed.
- `surviving_assumptions` is required non-empty for passed candidates (FC-05).
- `zero_issue_flag = true` triggers mandatory re-scan of assumption, leakage_risk, realism.

---

## 8. Recommendation

```jsonc
{
  "run_id": "string",
  "best_candidate_id": "string | null",
  "runner_up_candidate_id": "string | null",
  "rejected_candidate_ids": ["string"],
  "ranking_logic": [
    {
      "comparison_axis": "string",
      "best_assessment": "string",
      "runner_up_assessment": "string",
      "verdict": "string"
    }
  ],
  "open_unknowns": [
    {
      "unknown_id": "string",
      "description": "string",
      "impact_if_resolved_positively": "string",
      "impact_if_resolved_negatively": "string",
      "resolution_method": "string"
    }
  ],
  "critical_conditions": [
    {
      "condition_id": "string",
      "statement": "string",
      "verification_method": "string",
      "verification_timing": "string",
      "source": "string"
    }
  ],
  "confidence_label": "low | medium | high",
  "confidence_explanation": "string",
  "next_validation_steps": [
    {
      "step_id": "string",
      "who": "string",
      "what_data": "string",
      "what_test": "string",
      "threshold": "string",
      "priority": "critical | high | medium"
    }
  ],
  "recommendation_expiry": {
    "type": "time_based | event_based | evidence_based",
    "description": "string",
    "expiry_date": "ISO-8601 | null",
    "expiry_trigger": "string | null"
  }
}
```

Notes:
- `confidence_label` is mechanically determined (FC-02). No manual override.
- `open_unknowns` must be non-empty. Zero unknowns at plan stage is unrealistic.
- `critical_conditions` must be non-empty. Unconditional recommendations do not exist.
- `ranking_logic` must have ≥ 3 axes. "Overall judgment" is prohibited (FC-03).

---

## 9. CandidateCard (derived, user-facing)

```jsonc
{
  "candidate_id": "string",
  "label": "primary | alternative",
  "display_name": "string",
  "summary": "string",
  "strategy_approach": "string",
  "expected_return_band": {
    "low_pct": "number",
    "high_pct": "number",
    "basis": "string",
    "disclaimer": "string"
  },
  "estimated_max_loss": {
    "low_pct": "number",
    "high_pct": "number",
    "basis": "string"
  },
  "confidence_level": "low | medium | high",
  "confidence_reason": "string",
  "key_risks": ["string"],
  "stop_conditions_headline": "string"
}
```

Notes:
- This is a **derived object**. Generated from Candidate + Audit + Recommendation + TestResult at presentation time. Persisted for API serving but regenerated on demand if missing.
- All fields are mandatory. A card with any missing field is invalid.
- No other fields are shown to the user. Internal data points are compressed into these 8 fields.

---

## 10. PresentationContext (derived, user-facing)

```jsonc
{
  "run_id": "string",
  "created_at": "ISO-8601",
  "validation_summary": "string",
  "recommendation_expiry": "string",
  "rejection_headline": "string | null",
  "caveats": ["string"],
  "candidates_evaluated": "integer",
  "candidates_rejected": "integer",
  "candidates_presented": "integer"
}
```

---

## 11. Approval

```jsonc
{
  "approval_id": "string",
  "run_id": "string",
  "candidate_id": "string",
  "approved_at": "ISO-8601",
  "user_confirmations": {
    "risks_reviewed": true,
    "stop_conditions_reviewed": true,
    "paper_run_understood": true
  },
  "runtime_config": {
    "initial_virtual_capital": "number",
    "currency": "JPY | USD",
    "rebalance_frequency": "monthly",
    "cost_model": {
      "commission_bps": 10,
      "spread_bps": 10
    },
    "execution_timing": "T+1_open"
  },
  "stop_conditions": [
    {
      "id": "SC-01",
      "type": "max_drawdown",
      "threshold": -0.20,
      "action": "halt_and_notify"
    },
    {
      "id": "SC-02",
      "type": "consecutive_underperformance",
      "months": 3,
      "benchmark": "market_index",
      "action": "halt_and_notify"
    },
    {
      "id": "SC-03",
      "type": "signal_anomaly",
      "threshold_sigma": 3.0,
      "action": "pause_and_notify"
    },
    {
      "id": "SC-04",
      "type": "data_quality_failure",
      "consecutive_days": 3,
      "action": "pause_and_notify"
    }
  ],
  "re_evaluation": {
    "monthly_report": true,
    "quarterly_full_re_evaluation": true,
    "re_evaluation_triggers": ["string"]
  },
  "re_approval_required": ["string"]
}
```

Notes:
- `user_confirmations` must all be `true` for approval to be valid.
- `stop_conditions` are system-defined in v1. Not user-configurable. Each condition type has its own specific fields (`threshold`, `months` + `benchmark`, `threshold_sigma`, `consecutive_days`) rather than a generic threshold.
- `runtime_config` values are fixed in v1 except `initial_virtual_capital` and `currency`.

---

## 12. PaperRunState

```jsonc
{
  "paper_run_id": "string",
  "approval_id": "string",
  "candidate_id": "string",
  "started_at": "ISO-8601",
  "status": "running | paused | halted | re_evaluating",
  "current_snapshot": {
    "day_count": "integer",
    "virtual_capital_initial": "number",
    "virtual_capital_current": "number",
    "total_return_pct": "number",
    "current_drawdown_pct": "number",
    "positions_count": "integer",
    "last_rebalance": "ISO-8601",
    "next_rebalance": "ISO-8601"
  },
  "safety_status": {
    "any_breached": false,
    "nearest_condition": {
      "id": "string",
      "current_value": "number",
      "threshold": "number",
      "distance_pct": "number"
    }
  },
  "schedule": {
    "next_monthly_report": "ISO-8601",
    "next_quarterly_re_evaluation": "ISO-8601"
  },
  "halt_history": [
    {
      "halted_at": "ISO-8601",
      "condition_id": "string",
      "resumed_at": "ISO-8601 | null",
      "re_approval_id": "string | null"
    }
  ]
}
```

---

## 13. MonthlyReport

```jsonc
{
  "report_id": "string",
  "paper_run_id": "string",
  "period": { "start": "ISO-8601", "end": "ISO-8601" },
  "summary": "string",
  "numbers": {
    "monthly_return_pct": "number",
    "benchmark_return_pct": "number",
    "cumulative_return_pct": "number",
    "current_drawdown_pct": "number",
    "positions_count": "integer",
    "trades_this_month": "integer"
  },
  "safety_note": "string",
  "next": "string"
}
```

---

## 14. ReEvaluationResult

```jsonc
{
  "re_evaluation_id": "string",
  "paper_run_id": "string",
  "executed_at": "ISO-8601",
  "trigger": "quarterly_schedule | stop_condition_hit | market_regime_change | user_requested",
  "outcome": "continue | change_candidate | stop_all",
  "new_run_id": "string | null",
  "new_best_candidate_id": "string | null",
  "new_runner_up_candidate_id": "string | null",
  "explanation": "string",
  "re_approval_required": true
}
```

Notes:
- `outcome: "continue"` does not require re-approval. The system continues automatically.
- `outcome: "change_candidate"` generates a new Recommendation and CandidateCard pair, requiring re-approval.
- `outcome: "stop_all"` halts Paper Run. User can start a new run from scratch.

---

## 15. DataQualityReport (Execution Layer output)

```jsonc
{
  "evidence_item_id": "string",
  "acquisition_status": "acquired | partially_acquired | failed",
  "acquisition_timestamp": "ISO-8601",
  "data_source": "string",
  "row_count": "integer",
  "date_range_actual": { "start": "ISO-8601", "end": "ISO-8601" },
  "quality_issues": [
    {
      "check_type": "completeness | consistency | temporal | survivorship | pit",
      "severity": "info | warning | critical",
      "description": "string",
      "affected_rows": "integer",
      "affected_percentage": "number"
    }
  ],
  "pit_status_verified": "full | partial | none | not_applicable",
  "usable_for_validation": true
}
```

---

## 16. TestResult (Execution Layer output)

```jsonc
{
  "test_result_id": "string",
  "test_id": "string",
  "candidate_id": "string",
  "execution_status": "completed | partial | failed",
  "metrics_results": [
    {
      "metric_name": "string",
      "actual_value": "number",
      "pass_threshold": "string",
      "fail_threshold": "string",
      "result": "pass | fail | inconclusive",
      "statistical_significance": {
        "test_used": "string",
        "p_value": "number | null",
        "confidence_interval": ["number", "number"]
      }
    }
  ],
  "overall_result": "pass | fail | mixed",
  "return_timeseries": {
    "dates": ["ISO-8601"],
    "gross_returns": ["number"],
    "net_returns": ["number"],
    "benchmark_returns": ["number"]
  },
  "data_quality_flags": ["string"],
  "pit_compliance": "full | partial | none"
}
```

---

## 17. ComparisonResult (Execution Layer output)

```jsonc
{
  "comparison_id": "string",
  "run_id": "string",
  "comparison_matrix": {
    "candidates": ["string"],
    "baseline_candidate_id": "string",
    "metrics": [
      {
        "metric_name": "string",
        "values": {
          "{candidate_id}": {
            "value": "number",
            "vs_baseline": "number",
            "is_significant": true,
            "p_value": "number",
            "rank": "integer"
          }
        }
      }
    ]
  },
  "execution_based_rejections": [
    {
      "candidate_id": "string",
      "reason": "string",
      "disqualifying_test_results": ["string"]
    }
  ],
  "execution_based_ranking": {
    "recommended_best": "string | null",
    "recommended_runner_up": "string | null",
    "ranking_rationale": [
      {
        "comparison_axis": "string",
        "winner": "string",
        "margin": "string"
      }
    ]
  }
}
```

---

**Role of this document**: This is the single source of truth for all internal data structures in Give Me a DAY. Every module in the system reads from and writes to these objects. Implementation must validate enum values, referential integrity between objects, and mandatory field presence at write time. If a field is not defined here, it does not exist in the system.

---

**Fixes applied in this version**:
- §9 CandidateCard Notes: changed "not stored independently" to "Persisted for API serving but regenerated on demand if missing" (I-2)
- §11 Approval.stop_conditions: replaced generic `threshold: number | null` with per-type specific fields matching v1_output_spec.md (SC-01: `threshold`, SC-02: `months` + `benchmark`, SC-03: `threshold_sigma`, SC-04: `consecutive_days`) (B-2)
- §11 Approval Notes: added clarification that each condition type has its own specific fields
