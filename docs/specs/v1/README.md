# Give Me a DAY v1 — Technical Specifications

This directory contains the complete technical specifications for **Give Me a DAY v1**.

## Specification Files

| File | Description | Core Loop Step |
|------|-------------|----------------|
| [`core_loop_spec.md`](core_loop_spec.md) | Internal Core Loop Specification — 9-step processing pipeline | All steps |
| [`internal_schema_consolidated.md`](internal_schema_consolidated.md) | Consolidated internal schema — all data structures (single source of truth) | All steps |
| [`goal_intake_spec.md`](goal_intake_spec.md) | Goal Intake Design — UX and internal logic for Step 1 | Step 1 |
| [`domain_framing_spec.md`](domain_framing_spec.md) | Domain Framing Design — strategy archetypes and problem reframing | Step 2 |
| [`evidence_taxonomy_spec.md`](evidence_taxonomy_spec.md) | Evidence Taxonomy — data classification dictionary for validation | Step 5 |
| [`audit_rubric_spec.md`](audit_rubric_spec.md) | Audit Rubric — candidate evaluation and rejection criteria | Step 7 |
| [`output_package_spec.md`](output_package_spec.md) | Output Package — final recommendation deliverable structure | Step 8-9 |

## Reading Order

For understanding the system architecture:

1. **Start here**: `core_loop_spec.md` — Overview of all 9 steps
2. **Data model**: `internal_schema_consolidated.md` — All object definitions
3. **Step-by-step**: Follow the specific step specs as needed

## Document Dependencies

```
core_loop_spec.md
    ├── goal_intake_spec.md (Step 1)
    ├── domain_framing_spec.md (Step 2)
    ├── evidence_taxonomy_spec.md (Step 5)
    ├── audit_rubric_spec.md (Step 7)
    └── output_package_spec.md (Step 8-9)

internal_schema_consolidated.md
    └── Incorporates all above specs into unified schema
```

## Version Information

- **Version**: v1 draft
- **Domain**: Investment research / Strategy validation / Hypothesis-testing pipelines
- **Status**: Design phase — pre-implementation
- **Scope**: Planning-phase product (no backtest execution in v1)

## Key Design Principles

1. **Validation-first**: Generate validated direction, not just code
2. **Conditional recommendations**: All recommendations include explicit conditions and unknowns
3. **Rejection as value**: Weak candidates are explicitly rejected with reasons
4. **Transparency**: All assumptions, uncertainties, and limitations are surfaced

---

*These specifications define Give Me a DAY's core value: moving from high-level goals to conditionally recommended system directions through structured research and validation loops.*
