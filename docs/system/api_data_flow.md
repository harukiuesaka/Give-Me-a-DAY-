# Give Me a DAY v1 — API & Data Flow Design

**Document type**: Implementation-ready API and data flow specification
**Upstream**: All source of truth documents + technical_design.md
**Purpose**: Define entity relationships, module-to-module data flow, API boundaries, persistence strategy, and audit trail at implementation-ready granularity

---

## 1. Primary Entities

### Entity Classification

Entities fall into three lifecycle phases. This classification drives persistence strategy, access patterns, and API exposure.

```
Phase A: Pipeline (one-time, per run)
  UserIntent → DomainFrame → ResearchSpec → Candidate[] → EvidencePlan[] →
  ValidationPlan[] → TestResult[] → ComparisonResult → Audit[] → Recommendation

Phase B: Presentation + Approval (user-facing, per run)
  CandidateCard[] → PresentationContext → Approval

Phase C: Runtime (ongoing, per paper run)
  PaperRunState → MonthlyReport[] → ReEvaluationResult[]
```

### Entity Registry

| Entity | Schema Ref | Created By | Consumed By | Lifecycle | Mutable |
|--------|-----------|-----------|------------|-----------|---------|
| UserIntent | §1 | GoalIntake | DomainFramer, ResearchSpecCompiler | Run | No |
| DomainFrame | §2 | DomainFramer | ResearchSpecCompiler, CandidateGenerator | Run | No |
| ResearchSpec | §3 | ResearchSpecCompiler | EvidencePlanner, CandidateGenerator, ValidationPlanner, AuditEngine | Run | No |
| Candidate | §4 | CandidateGenerator | EvidencePlanner, ValidationPlanner, AuditEngine, RecommendationEngine, ReportingEngine | Run | No |
| EvidencePlan | §5 | EvidencePlanner | ValidationPlanner, AuditEngine, RecommendationEngine | Run | Updated once (after data acquisition) |
| DataQualityReport | §15 | ExecutionLayer | AuditEngine | Run | No |
| ValidationPlan | §6 | ValidationPlanner | ExecutionLayer, AuditEngine | Run | No |
| TestResult | §16 | ExecutionLayer | AuditEngine, RecommendationEngine, ReportingEngine | Run | No |
| ComparisonResult | §17 | ExecutionLayer | AuditEngine, RecommendationEngine | Run | No |
| Audit | §7 | AuditEngine | RecommendationEngine, ReportingEngine | Run | No |
| Recommendation | §8 | RecommendationEngine | ReportingEngine | Run | No |
| CandidateCard | §9 | ReportingEngine | User (presentation) | Run | No (derived) |
| PresentationContext | §10 | ReportingEngine | User (presentation) | Run | No (derived) |
| Approval | §11 | User (via approval screen) | ExecutionLayer (Paper Run) | Run→Runtime | No |
| PaperRunState | §12 | ExecutionLayer | ReportingEngine, User (status card) | Runtime | Yes (daily) |
| MonthlyReport | §13 | ReportingEngine | User (notification) | Runtime | No |
| ReEvaluationResult | §14 | ExecutionLayer + AuditEngine + RecommendationEngine | ReportingEngine, User | Runtime | No |

### Entity ID Conventions

| Entity | ID Format | Example |
|--------|-----------|---------|
| Run | `run_{uuid8}` | `run_a1b2c3d4` |
| Candidate | `{run_id}_C{nn}` | `run_a1b2c3d4_C01` |
| EvidencePlan | `{run_id}_EP_{candidate_suffix}` | `run_a1b2c3d4_EP_C01` |
| ValidationPlan | `{run_id}_VP_{candidate_suffix}` | `run_a1b2c3d4_VP_C01` |
| Test | `{run_id}_T_{candidate_suffix}_{nn}` | `run_a1b2c3d4_T_C01_01` |
| TestResult | `{run_id}_TR_{test_suffix}` | `run_a1b2c3d4_TR_C01_01` |
| Audit | `{run_id}_AU_{candidate_suffix}` | `run_a1b2c3d4_AU_C01` |
| Approval | `{run_id}_AP` | `run_a1b2c3d4_AP` |
| PaperRun | `pr_{uuid8}` | `pr_e5f6g7h8` |
| MonthlyReport | `{paper_run_id}_MR_{YYYYMM}` | `pr_e5f6g7h8_MR_202604` |
| ReEvaluation | `{paper_run_id}_RE_{nn}` | `pr_e5f6g7h8_RE_01` |

---

## 2. Module-to-Module Data Flow

### Pipeline Phase (synchronous, one-time per run)

```
GoalIntake
  writes: UserIntent
  reads:  (user input)
     │
     │ UserIntent
     ↓
DomainFramer
  writes: DomainFrame
  reads:  UserIntent
     │
     │ DomainFrame
     ↓
ResearchSpecCompiler
  writes: ResearchSpec
  reads:  UserIntent, DomainFrame
     │
     │ ResearchSpec
     ↓
CandidateGenerator
  writes: Candidate[]
  reads:  ResearchSpec, DomainFrame
     │                              ┌─────────────────────┐
     │ Candidate[]                  │                     │
     ↓                              ↓                     │
EvidencePlanner                ExecutionLayer.DataAcq      │
  writes: EvidencePlan[]          writes: raw data files    │
  reads:  ResearchSpec,                   DataQualityReport[]
          Candidate[],            reads:  EvidencePlan[]    │
          acquired data                                    │
     │                                                     │
     │ EvidencePlan[]                                      │
     ↓                                                     │
ValidationPlanner                                          │
  writes: ValidationPlan[]                                 │
  reads:  ResearchSpec, Candidate[], EvidencePlan[]        │
     │                                                     │
     │ ValidationPlan[]                                    │
     ↓                                                     │
ExecutionLayer.ValidationExec                              │
  writes: TestResult[], ComparisonResult                   │
  reads:  ValidationPlan[], acquired data                  │
     │                                                     │
     │ TestResult[], ComparisonResult                      │
     ↓                                                     │
AuditEngine                                                │
  writes: Audit[]                                          │
  reads:  Candidate[], EvidencePlan[], ValidationPlan[],   │
          TestResult[], ComparisonResult, ResearchSpec      │
     │                                                     │
     │ Audit[] ── all rejected? ──→ CandidateGenerator ───┘
     │                              (once, with rejection constraints)
     ↓
RecommendationEngine
  writes: Recommendation
  reads:  Audit[], Candidate[], ComparisonResult,
          ResearchSpec, EvidencePlan[]
     │
     │ Recommendation
     ↓
ReportingEngine
  writes: CandidateCard[], PresentationContext
  reads:  Recommendation, Candidate[], Audit[], TestResult[]
     │
     │ CandidateCard[], PresentationContext
     ↓
  → User (presentation screen)
```

### Approval Phase (user-triggered)

```
User (selects candidate, confirms risks)
     │
     │ candidate_id + confirmations + virtual_capital
     ↓
ApprovalHandler
  writes: Approval
  reads:  Recommendation, CandidateCard (selected)
     │
     │ Approval
     ↓
ExecutionLayer.PaperRunInit
  writes: PaperRunState (initial)
  reads:  Approval, Candidate (approved)
     │
     │ PaperRunState
     ↓
  → User (status card) + scheduler registered for daily cycle
```

### Runtime Phase (scheduled, ongoing)

```
Scheduler (daily trigger, market close + 1hr)
     │
     ↓
ExecutionLayer.PaperRunDailyCycle
  writes: PaperRunState (updated snapshot)
  reads:  PaperRunState (previous), market data (fetched)
     │
     │ if stop_condition_breached:
     │   writes: halt event in PaperRunState.halt_history
     │   → NotificationService → User
     │
     │ if month_end:
     ↓
ReportingEngine.MonthlyReport
  writes: MonthlyReport
  reads:  PaperRunState (month's snapshots)
     │
     │ MonthlyReport
     ↓
NotificationService → User (push + email)


Scheduler (quarterly trigger)
     │
     ↓
ExecutionLayer.ReEvaluation
  executes: Core Loop Steps 5–8 with fresh data
  writes: ReEvaluationResult
  reads:  PaperRunState, original ResearchSpec, original DomainFrame
     │
     │ ReEvaluationResult
     ├─ outcome=continue → auto-resume, notify user (normal)
     ├─ outcome=change_candidate → new CandidateCards → User (re-approval required)
     └─ outcome=stop_all → halt PaperRun → User (urgent notification)
```

---

## 3. Request / Response Flow

### Flow A: Pipeline Execution (POST /runs)

```
Client                          Server
  │                               │
  │  POST /runs                   │
  │  {goal, success_criteria,     │
  │   risk, time_horizon,         │
  │   exclusions}                 │
  │ ─────────────────────────→    │
  │                               │ → GoalIntake
  │                               │ → DomainFramer
  │  202 Accepted                 │ → ResearchSpecCompiler
  │  {run_id, status_url}         │ → CandidateGenerator
  │ ←─────────────────────────    │ → EvidencePlanner + DataAcq
  │                               │ → ValidationPlanner
  │  GET /runs/{run_id}/status    │ → ExecutionLayer
  │ ─────────────────────────→    │ → AuditEngine
  │                               │ → RecommendationEngine
  │  {status: "executing",        │ → ReportingEngine
  │   step: "backtesting",        │
  │   progress: 4/7}              │
  │ ←─────────────────────────    │
  │                               │
  │  ... (polling or SSE) ...     │
  │                               │
  │  GET /runs/{run_id}/status    │
  │ ─────────────────────────→    │
  │                               │
  │  {status: "completed",        │
  │   result_url}                 │
  │ ←─────────────────────────    │
  │                               │
  │  GET /runs/{run_id}/result    │
  │ ─────────────────────────→    │
  │                               │
  │  {candidate_cards: [...],     │
  │   presentation_context: {...},│
  │   approval_url}               │
  │ ←─────────────────────────    │
```

### Flow B: Approval (POST /runs/{run_id}/approve)

```
Client                          Server
  │                               │
  │  POST /runs/{run_id}/approve  │
  │  {candidate_id,               │
  │   user_confirmations: {       │
  │     risks_reviewed: true,     │
  │     stop_conditions_reviewed: │
  │       true,                   │
  │     paper_run_understood: true│
  │   },                          │
  │   virtual_capital: 1000000}   │
  │ ─────────────────────────→    │
  │                               │ → Validate confirmations (all true)
  │                               │ → Create Approval object
  │                               │ → Initialize PaperRunState
  │                               │ → Register daily scheduler
  │  201 Created                  │
  │  {approval_id,                │
  │   paper_run_id,               │
  │   status_url}                 │
  │ ←─────────────────────────    │
```

### Flow C: Paper Run Status (GET /paper-runs/{id})

```
Client                          Server
  │                               │
  │  GET /paper-runs/{id}         │
  │ ─────────────────────────→    │
  │                               │ → Load PaperRunState
  │  {status: "running",          │
  │   day_count: 32,              │
  │   current_value: 1024300,     │
  │   total_return_pct: 2.4,      │
  │   safety: "all_clear",        │
  │   next_report: "2026-04-16",  │
  │   next_re_eval: "2026-06-16"} │
  │ ←─────────────────────────    │
```

### Flow D: Manual Stop (POST /paper-runs/{id}/stop)

```
Client                          Server
  │                               │
  │  POST /paper-runs/{id}/stop   │
  │ ─────────────────────────→    │
  │                               │ → Set status = halted
  │                               │ → Record in halt_history
  │  200 OK                       │
  │  {status: "halted",           │
  │   resume_requires: "re-approval"}
  │ ←─────────────────────────    │
```

### Flow E: Re-approval after halt or re-evaluation (POST /paper-runs/{id}/re-approve)

```
Client                          Server
  │                               │
  │  POST /paper-runs/{id}/       │
  │        re-approve             │
  │  {candidate_id,               │
  │   user_confirmations: {...}}  │
  │ ─────────────────────────→    │
  │                               │ → Create new Approval
  │                               │ → Resume or start new PaperRun
  │  201 Created                  │
  │  {new_approval_id,            │
  │   paper_run_status: "running"}│
  │ ←─────────────────────────    │
```

---

## 4. Read / Write Mapping to internal_schema

### Write Map (which module writes which entity)

| Entity | Writer Module | Write Trigger | Write Frequency |
|--------|--------------|---------------|----------------|
| UserIntent | GoalIntake | User submits goal | Once per run |
| DomainFrame | DomainFramer | After GoalIntake completes | Once per run |
| ResearchSpec | ResearchSpecCompiler | After DomainFramer completes | Once per run |
| Candidate | CandidateGenerator | After ResearchSpecCompiler (or after all-rejection retry) | Once per run (twice if retry) |
| EvidencePlan | EvidencePlanner | After CandidateGenerator + after DataAcquisition | Twice per run (plan + update) |
| DataQualityReport | ExecutionLayer.DataAcq | After each data source acquired | N per run (one per evidence item) |
| ValidationPlan | ValidationPlanner | After EvidencePlanner completes | Once per run per candidate |
| TestResult | ExecutionLayer.ValidationExec | After each test completes | N per run (one per test per candidate) |
| ComparisonResult | ExecutionLayer.ComparisonEngine | After all TestResults generated | Once per run |
| Audit | AuditEngine | After ComparisonResult (or per candidate) | Once per run per candidate |
| Recommendation | RecommendationEngine | After all Audits complete | Once per run |
| CandidateCard | ReportingEngine | After Recommendation | Once per run (derived, 0–2 cards) |
| PresentationContext | ReportingEngine | After Recommendation | Once per run (derived) |
| Approval | ApprovalHandler | User approves | Once per approval event |
| PaperRunState | ExecutionLayer.PaperRun | Daily cycle | Once per trading day |
| MonthlyReport | ReportingEngine | Month end | Once per month |
| ReEvaluationResult | ExecutionLayer.ReEval | Quarterly or triggered | Once per re-evaluation event |

### Read Map (which module reads which entity)

| Entity | Reader Modules |
|--------|---------------|
| UserIntent | DomainFramer, ResearchSpecCompiler |
| DomainFrame | ResearchSpecCompiler, CandidateGenerator |
| ResearchSpec | CandidateGenerator, EvidencePlanner, ValidationPlanner, AuditEngine, RecommendationEngine |
| Candidate | EvidencePlanner, ValidationPlanner, AuditEngine, RecommendationEngine, ReportingEngine, ExecutionLayer.PaperRun |
| EvidencePlan | ValidationPlanner, AuditEngine, RecommendationEngine |
| DataQualityReport | AuditEngine |
| ValidationPlan | ExecutionLayer.ValidationExec, AuditEngine |
| TestResult | AuditEngine, RecommendationEngine, ReportingEngine |
| ComparisonResult | AuditEngine, RecommendationEngine |
| Audit | RecommendationEngine, ReportingEngine |
| Recommendation | ReportingEngine, ApprovalHandler |
| CandidateCard | User (presentation), ApprovalHandler |
| PresentationContext | User (presentation) |
| Approval | ExecutionLayer.PaperRun |
| PaperRunState | ReportingEngine, User (status card), ExecutionLayer.ReEval |
| MonthlyReport | User (notification) |
| ReEvaluationResult | ReportingEngine, User (notification) |

---

## 5. API Endpoint Candidates

### v1 API Surface

v1 exposes a minimal API. The user-facing application (web or mobile) is the only client.

| Method | Path | Purpose | Auth | Response |
|--------|------|---------|------|----------|
| `POST` | `/api/v1/runs` | Start a new pipeline run | User session | 202 + run_id + status_url |
| `GET` | `/api/v1/runs/{run_id}/status` | Poll pipeline progress | User session | Progress object |
| `GET` | `/api/v1/runs/{run_id}/result` | Get candidate presentation | User session | CandidateCard[] + PresentationContext |
| `GET` | `/api/v1/runs/{run_id}/export` | Download Markdown export | User session | Markdown text |
| `POST` | `/api/v1/runs/{run_id}/approve` | Approve a candidate, start Paper Run | User session | 201 + approval_id + paper_run_id |
| `GET` | `/api/v1/paper-runs/{pr_id}` | Get Paper Run status card | User session | PaperRunState (user-facing subset) |
| `POST` | `/api/v1/paper-runs/{pr_id}/stop` | Manually stop Paper Run | User session | 200 + halted status |
| `POST` | `/api/v1/paper-runs/{pr_id}/re-approve` | Re-approve after halt or re-eval | User session | 201 + new approval |
| `GET` | `/api/v1/paper-runs/{pr_id}/reports` | List monthly reports | User session | MonthlyReport[] |
| `GET` | `/api/v1/paper-runs/{pr_id}/reports/{id}` | Get specific monthly report | User session | MonthlyReport |

### Status endpoint detail

`GET /api/v1/runs/{run_id}/status` returns:

```jsonc
{
  "run_id": "string",
  "status": "pending | executing | completed | failed",
  "current_step": "goal_intake | domain_framing | research_spec | candidate_generation | data_acquisition | backtest_execution | statistical_testing | comparison | audit | recommendation | reporting",
  "steps_completed": 4,
  "steps_total": 7,
  "estimated_remaining_seconds": 180,
  "error": null                        // Non-null only if status = failed
}
```

Steps presented to user (7 steps, mapped from 11 internal modules):

| User-facing step | Internal modules |
|-----------------|-----------------|
| 方向性を設計中 | GoalIntake + DomainFramer + ResearchSpecCompiler + CandidateGenerator |
| データを取得中 | EvidencePlanner + ExecutionLayer.DataAcq |
| バックテストを実行中 | ValidationPlanner + ExecutionLayer.ValidationExec (backtest) |
| 統計的な検定を実施中 | ExecutionLayer.ValidationExec (statistical tests) |
| 候補を比較中 | ExecutionLayer.ComparisonEngine |
| 弱い方向を棄却判定中 | AuditEngine |
| 推奨パッケージを作成中 | RecommendationEngine + ReportingEngine |

### Result endpoint detail

`GET /api/v1/runs/{run_id}/result` returns:

```jsonc
{
  "run_id": "string",
  "candidate_cards": [
    {
      // CandidateCard schema (internal_schema §9)
      // All fields present. No internal IDs exposed except candidate_id.
    }
  ],
  "presentation_context": {
    // PresentationContext schema (internal_schema §10)
  },
  "approval_url": "/api/v1/runs/{run_id}/approve"
}
```

### What the API does NOT expose

| Not Exposed | Reason |
|-------------|--------|
| DomainFrame | Internal pipeline state |
| ResearchSpec | Internal specification |
| EvidencePlan details | Internal evidence assessment |
| ValidationPlan details | Internal test planning |
| TestResult numbers | Conclusions reflected in CandidateCard |
| ComparisonResult matrix | System has already compared and decided |
| Audit issue list | Conclusions reflected in key_risks and rejection_summary |
| Recommendation.ranking_logic detail | System has already ranked |
| Recommendation.open_unknowns full list | Top items reflected in CandidateCard; full list in optional detail report |
| Raw backtest data | Internal execution output |

If v1.5 adds a "detail mode," a separate `/api/v1/runs/{run_id}/detail` endpoint will expose selected internal objects. v1 does not expose them.

---

## 6. Persistence Design

### Storage Architecture

```
/data/
├── runs/
│   └── {run_id}/
│       ├── meta.json                     # run_id, created_at, status, user_id
│       ├── pipeline/
│       │   ├── user_intent.json
│       │   ├── domain_frame.json
│       │   ├── research_spec.json
│       │   ├── candidates/
│       │   │   ├── C01.json
│       │   │   ├── C02.json
│       │   │   └── C03.json
│       │   ├── evidence_plans/
│       │   │   ├── C01.json
│       │   │   ├── C02.json
│       │   │   └── C03.json
│       │   ├── data_quality/
│       │   │   ├── EI_C01_001.json
│       │   │   └── ...
│       │   ├── validation_plans/
│       │   │   ├── C01.json
│       │   │   ├── C02.json
│       │   │   └── C03.json
│       │   ├── test_results/
│       │   │   ├── TR_C01_01.json
│       │   │   └── ...
│       │   ├── comparison_result.json
│       │   ├── audits/
│       │   │   ├── C01.json
│       │   │   ├── C02.json
│       │   │   └── C03.json
│       │   └── recommendation.json
│       ├── presentation/
│       │   ├── candidate_cards.json      # Array of 0–2 cards
│       │   ├── presentation_context.json
│       │   └── markdown_export.md
│       └── approval.json                 # null until approved
│
├── paper_runs/
│   └── {paper_run_id}/
│       ├── meta.json                     # paper_run_id, approval_id, run_id, started_at
│       ├── state.json                    # Current PaperRunState (overwritten daily)
│       ├── snapshots/
│       │   ├── 2026-03-16.json
│       │   ├── 2026-03-17.json
│       │   └── ...
│       ├── reports/
│       │   ├── MR_202604.json
│       │   └── ...
│       ├── re_evaluations/
│       │   ├── RE_01.json
│       │   └── ...
│       └── signals/                      # 90-day rolling
│           ├── 2026-03-16.json
│           └── ...
│
└── evidence/                             # Raw data files (shared across runs)
    ├── price/
    │   ├── JP_daily_OHLCV.parquet
    │   └── US_daily_OHLCV.parquet
    ├── macro/
    │   ├── FRED_GDP.parquet
    │   └── FRED_VIX.parquet
    ├── metadata/
    │   ├── TOPIX_constituents.parquet
    │   └── SP500_constituents.parquet
    └── user_uploads/
        └── {run_id}/
            └── uploaded_file.parquet
```

### Storage Format Rules

| Data Type | Format | Reason |
|-----------|--------|--------|
| Schema objects (UserIntent, Audit, etc.) | JSON | Human-readable, easy to debug, schema-validatable |
| Time series data (prices, returns) | Parquet | Columnar, compressed, fast for pandas operations |
| Daily PaperRun snapshots | JSON | Small, one per day, append-only pattern |
| Monthly reports | JSON | Schema-validated output |
| Markdown export | .md file | Direct user download |

### Write Patterns

| Pattern | Entities | Characteristics |
|---------|---------|----------------|
| Write-once (pipeline) | UserIntent, DomainFrame, ResearchSpec, Candidate, ValidationPlan, TestResult, ComparisonResult, Audit, Recommendation, CandidateCard, PresentationContext | Written once during pipeline execution. Never modified. |
| Write-then-update (evidence) | EvidencePlan | Written during planning, updated after data acquisition with actual availability and quality |
| Write-on-event (approval) | Approval | Written when user approves. Never modified |
| Daily overwrite (runtime state) | PaperRunState.state.json | Overwritten daily. Previous state preserved in snapshots/ |
| Append-only (runtime history) | PaperRunState snapshots, MonthlyReport, ReEvaluationResult, signal history | New files appended. Never modified or deleted |

### Retention Policy

| Data | Retention | Reason |
|------|-----------|--------|
| Pipeline objects (per run) | 1 year after run completion | Audit trail for past recommendations |
| Raw evidence data | Shared, updated with new data | Reused across runs |
| Paper Run state + snapshots | Lifetime of Paper Run + 1 year | Performance tracking, re-evaluation baseline |
| Monthly reports | Indefinite | User-accessible history |
| Signal history | 90 days rolling | Anomaly detection window |
| User uploads | 1 year after run completion | May be needed for re-evaluation |

### Backup Strategy

| Component | Strategy | Frequency |
|-----------|----------|-----------|
| Pipeline objects | Copy-on-write (backup before any overwrite) | On each write |
| PaperRunState | Daily snapshot is the backup | Daily |
| Evidence data (Parquet) | Nightly copy to backup directory | Nightly |
| All JSON files | Git-like versioning (optional, v1.5) | — |

---

## 7. Audit Trail Design

### What the audit trail must answer

1. **For any recommendation**: Why was this candidate recommended? What was compared? What was rejected and why?
2. **For any rejection**: Which specific Audit issues caused disqualification? What data supported the severity judgment?
3. **For any Paper Run halt**: Which stop condition was breached? What was the state at breach time? When was the user notified?
4. **For any re-evaluation**: What changed in the data? Did the recommendation change? Was re-approval obtained?

### Audit Events

Every significant action is recorded as an audit event:

```jsonc
{
  "event_id": "string",
  "timestamp": "ISO-8601",
  "run_id": "string",
  "paper_run_id": "string | null",
  "event_type": "string",
  "module": "string",
  "details": {}
}
```

| Event Type | Module | Trigger | Details Content |
|-----------|--------|---------|----------------|
| `pipeline.started` | Orchestrator | POST /runs | {run_id, raw_goal} |
| `pipeline.step_completed` | Each module | Module output written | {step_name, duration_ms, output_entity_ids} |
| `pipeline.step_failed` | Each module | Module exception | {step_name, error_type, error_message, fallback_action} |
| `candidate.generated` | CandidateGenerator | Candidates created | {candidate_ids, types, diversity_score} |
| `candidate.regenerated` | CandidateGenerator | All-rejection retry | {old_candidate_ids, new_candidate_ids, rejection_constraints} |
| `data.acquired` | ExecutionLayer.DataAcq | Data source fetched | {source, rows, quality_issues_count} |
| `data.acquisition_failed` | ExecutionLayer.DataAcq | Fetch failure | {source, error, fallback} |
| `test.completed` | ExecutionLayer.ValidationExec | Test finished | {test_id, candidate_id, result: pass/fail/mixed} |
| `test.failed` | ExecutionLayer.ValidationExec | Test error/timeout | {test_id, error, partial_results} |
| `audit.issue_found` | AuditEngine | Issue detected | {candidate_id, issue_id, severity, category, disqualifying} |
| `audit.candidate_rejected` | AuditEngine | Candidate fails audit | {candidate_id, rejection_reason_summary, disqualifying_issues} |
| `audit.candidate_passed` | AuditEngine | Candidate passes audit | {candidate_id, status, surviving_assumptions_count, residual_risks_count} |
| `recommendation.generated` | RecommendationEngine | Recommendation created | {best_id, runner_up_id, rejected_count, confidence_label} |
| `recommendation.null` | RecommendationEngine | All candidates rejected | {reason_summary, alternative_directions} |
| `presentation.generated` | ReportingEngine | Cards created | {cards_count, presentation_context_summary} |
| `approval.submitted` | ApprovalHandler | User approves | {candidate_id, virtual_capital, confirmations} |
| `paper_run.started` | ExecutionLayer.PaperRun | After approval | {paper_run_id, candidate_id, config} |
| `paper_run.daily_completed` | ExecutionLayer.PaperRun | Daily cycle done | {date, return_pct, drawdown_pct, stop_conditions_status} |
| `paper_run.stop_approaching` | ExecutionLayer.PaperRun | Stop condition proximity | {condition_id, current_value, threshold, distance_pct} |
| `paper_run.halted` | ExecutionLayer.PaperRun | Stop condition hit | {condition_id, breach_value, threshold} |
| `paper_run.paused` | ExecutionLayer.PaperRun | Anomaly or data failure | {reason, details} |
| `paper_run.manual_stop` | User | User stops Paper Run | {user_action: "manual_stop"} |
| `re_evaluation.started` | ExecutionLayer.ReEval | Quarterly or triggered | {trigger, paper_run_id} |
| `re_evaluation.completed` | ExecutionLayer.ReEval | Re-evaluation done | {outcome, new_recommendation_summary} |
| `re_approval.submitted` | User | User re-approves | {new_candidate_id, previous_candidate_id} |
| `notification.sent` | NotificationService | Any notification | {type, urgency, channel, delivery_status} |

### Audit Event Storage

```
/data/audit_log/
├── {run_id}/
│   ├── pipeline_events.jsonl          # One JSON object per line
│   └── approval_events.jsonl
└── {paper_run_id}/
    ├── runtime_events.jsonl           # Daily events, append-only
    ├── halt_events.jsonl              # Halt/pause events
    └── re_evaluation_events.jsonl
```

Format: JSON Lines (`.jsonl`). One event per line. Append-only. Never modified or deleted.

### Audit Trail Queries (v1: file scan, v1.5: indexed database)

| Query | Method in v1 |
|-------|-------------|
| "Why was candidate C03 rejected?" | Scan pipeline_events.jsonl for `audit.candidate_rejected` where candidate_id = C03 |
| "What stop condition halted this Paper Run?" | Read halt_events.jsonl, find latest `paper_run.halted` |
| "What changed in the quarterly re-evaluation?" | Read re_evaluation_events.jsonl for `re_evaluation.completed` |
| "How long did the pipeline take?" | Sum duration_ms from `pipeline.step_completed` events |

---

## 8. Recommendation Package Generation Flow

The "recommendation package" is not a single entity. It is a rendering operation that assembles multiple entities into user-facing output. This is the exact sequence:

```
Step 1: Collect inputs
  recommendation = PersistenceStore.load("recommendation", run_id)
  candidates = PersistenceStore.load_all("candidates", run_id)
  audits = PersistenceStore.load_all("audits", run_id)
  test_results = PersistenceStore.load_all("test_results", run_id)

Step 2: Generate CandidateCards (0–2)
  for each of [best_candidate_id, runner_up_candidate_id]:
    if id is not null:
      candidate = lookup(candidates, id)
      audit = lookup(audits, id)
      results = filter(test_results, candidate_id=id)

      card = CandidateCard(
        candidate_id = id,
        label = "primary" if id == best else "alternative",
        display_name = translate_to_plain_language(candidate.name),
        summary = simplify(candidate.summary, max_sentences=2),
        strategy_approach = one_sentence(candidate),
        expected_return_band = derive_from_test_results(results),
        estimated_max_loss = derive_from_test_results(results),
        confidence_level = recommendation.confidence_label,
        confidence_reason = first_sentence(recommendation.confidence_explanation),
        key_risks = translate_risks(audit.residual_risks[:3]),
        stop_conditions_headline = format_stop_conditions()
      )
      validate_all_fields_present(card)
      cards.append(card)

Step 3: Generate PresentationContext
  context = PresentationContext(
    run_id = run_id,
    created_at = recommendation.created_at,
    validation_summary = f"{len(candidates)}方向を検討、{count_rejected(audits)}方向を棄却、{count_tests(test_results)}種の検証を実施",
    recommendation_expiry = recommendation.recommendation_expiry.description,
    rejection_headline = summarize_rejections(audits),
    caveats = collect_execution_caveats(test_results, evidence_plans),
    candidates_evaluated = len(candidates),
    candidates_rejected = count_rejected(audits),
    candidates_presented = len(cards)
  )

Step 4: Validate output
  assert len(cards) == context.candidates_presented
  if len(cards) == 0:
    assert context.rejection_headline is not None
    assert len(alternative_directions) >= 3

Step 5: Persist
  PersistenceStore.save("candidate_cards", run_id, cards)
  PersistenceStore.save("presentation_context", run_id, context)

Step 6: Generate Markdown export
  markdown = render_markdown_template(cards, context)
  PersistenceStore.save_file(f"runs/{run_id}/presentation/markdown_export.md", markdown)

Step 7: Return to API
  return {
    candidate_cards: cards,
    presentation_context: context,
    approval_url: f"/api/v1/runs/{run_id}/approve"
  }
```

### CandidateCard derivation rules

| Card Field | Source | Derivation |
|-----------|--------|-----------|
| display_name | Candidate.name | Remove English jargon, translate to plain Japanese |
| summary | Candidate.summary | Shorten to 2 sentences max. Remove technical terms |
| strategy_approach | Candidate.architecture_outline | 1-sentence plain description of what the strategy does |
| expected_return_band.low_pct | TestResult (backtest, conservative estimate) | 25th percentile of rolling returns |
| expected_return_band.high_pct | TestResult (backtest, optimistic estimate) | 75th percentile of rolling returns |
| estimated_max_loss.low_pct | TestResult (backtest, less severe) | Average max drawdown across regimes |
| estimated_max_loss.high_pct | TestResult (backtest, more severe) | Worst max drawdown across regimes |
| confidence_level | Recommendation.confidence_label | Direct copy (mechanically calculated) |
| confidence_reason | Recommendation.confidence_explanation | First sentence only |
| key_risks | Audit.residual_risks | Top 3, translated to plain language |
| stop_conditions_headline | Approval.stop_conditions[0] | Format as "損失が-20%で自動停止" |

If TestResults are unavailable (planning-only fallback), return bands are estimated from comparable_known_approaches with wider ranges and a caveat added.

---

## 9. Synchronous Processing (v1)

### Everything in the pipeline is synchronous

The pipeline from GoalIntake to ReportingEngine runs as a single synchronous job triggered by `POST /runs`. The client polls `/runs/{run_id}/status` for progress.

Why synchronous:
- Pipeline steps have strict dependencies (DomainFrame needs UserIntent, ResearchSpec needs both, etc.)
- No step can meaningfully start before its predecessor completes
- Total pipeline time is ≤ 10 minutes — acceptable for a polling/SSE pattern
- Async orchestration adds complexity without benefit for a single-user sequential pipeline

### Pipeline execution model

```python
def execute_pipeline(raw_input) -> str:
    """
    Runs as a background job. Returns run_id.
    Client polls status endpoint for progress.
    """
    run_id = generate_run_id()
    update_status(run_id, "executing", step="goal_intake", progress="1/7")

    try:
        intent = GoalIntake.process(raw_input)
        persist(intent)

        frame = DomainFramer.frame(intent)
        persist(frame)

        spec = ResearchSpecCompiler.compile(intent, frame)
        persist(spec)

        candidates = CandidateGenerator.generate(spec, frame)
        persist(candidates)
        update_status(run_id, "executing", step="data_acquisition", progress="2/7")

        evidence_plans = []
        for c in candidates:
            ep = EvidencePlanner.plan(spec, c)
            evidence_plans.append(ep)
        data_results = ExecutionLayer.acquire_data(evidence_plans)
        for ep in evidence_plans:
            EvidencePlanner.update_with_acquired_data(ep, data_results)
            persist(ep)
        update_status(run_id, "executing", step="backtesting", progress="3/7")

        validation_plans = [ValidationPlanner.plan(spec, c, e)
                           for c, e in zip(candidates, evidence_plans)]
        persist(validation_plans)

        test_results, comparison = ExecutionLayer.execute_validation(
            validation_plans, evidence_plans, timeout=300
        )
        persist(test_results)
        persist(comparison)
        update_status(run_id, "executing", step="audit", progress="6/7")

        audits = [AuditEngine.audit(c, e, v, test_results, comparison, spec)
                  for c, e, v in zip(candidates, evidence_plans, validation_plans)]

        # All-rejection retry (once)
        if all(a.audit_status == "rejected" for a in audits):
            constraints = extract_rejection_constraints(audits)
            candidates = CandidateGenerator.generate(spec, frame, constraints)
            # Re-run evidence, validation, audit
            evidence_plans = [EvidencePlanner.plan(spec, c) for c in candidates]
            # ... (same sequence as above)
            audits = [AuditEngine.audit(...) for ...]

        persist(audits)

        recommendation = RecommendationEngine.generate(
            audits, candidates, comparison, spec, evidence_plans
        )
        persist(recommendation)
        update_status(run_id, "executing", step="reporting", progress="7/7")

        cards, context = ReportingEngine.generate_presentation(
            recommendation, candidates, audits, test_results
        )
        persist(cards, context)

        update_status(run_id, "completed")
        return run_id

    except Exception as e:
        log_error(run_id, e)
        update_status(run_id, "failed", error=str(e))
        raise
```

### Approval is synchronous and immediate

`POST /runs/{run_id}/approve` is a synchronous request:
1. Validate confirmations
2. Create Approval object
3. Initialize PaperRunState
4. Register daily scheduler
5. Return 201

No async processing needed. The Paper Run scheduler handles the ongoing daily cycle.

### Paper Run status queries are synchronous reads

`GET /paper-runs/{id}` reads the latest PaperRunState from disk. No computation needed.

---

## 10. Asynchronous / Deferred Processing (v1)

### Paper Run daily cycle: scheduled async

The daily cycle runs as a scheduled job, not triggered by user action:

```
Scheduler (cron or equivalent)
  │
  │ Every trading day at market close + 1 hour (JST 16:00 for JP, EST 17:00 for US)
  │
  ↓
PaperRunDailyCycle.run(paper_run_id)
  │
  ├── Fetch market data (async I/O, with retry)
  ├── Calculate signals
  ├── Update portfolio
  ├── Check stop conditions
  ├── Save snapshot
  │
  ├── IF stop condition → send notification (async)
  └── IF month end → trigger monthly report generation (async)
```

Implementation: Python script triggered by cron. Each Paper Run has a cron entry registered at approval time and removed at halt/stop.

### Monthly report generation: async after month end

Triggered by the daily cycle detecting month end. Runs as a separate job after the daily cycle completes. The user receives a push notification when the report is ready.

### Quarterly re-evaluation: async scheduled job

Triggered by a quarterly cron entry. Re-runs Core Loop Steps 5–8. Can take 5–10 minutes (same as initial pipeline). During execution, PaperRunState.status = "re_evaluating".

### Notification delivery: async fire-and-forget

All notifications (push, email) are sent asynchronously after the triggering event. Delivery failure is logged but does not block the triggering process.

### What is NOT async in v1

| Component | Why not async |
|-----------|---------------|
| Pipeline execution (Steps 1–9) | Sequential dependencies. No parallelism benefit |
| Approval processing | Simple write. Takes <100ms |
| Status queries | Simple read. Takes <10ms |
| Markdown export | Simple template render. Takes <1s |

### v1.5 async candidates

| Component | Why defer to v1.5 |
|-----------|-------------------|
| Parallel backtest execution across candidates | Adds complexity. v1 runs 3–5 candidates sequentially (~2 min each). Total ≤10 min is acceptable |
| Real-time re-evaluation trigger monitoring | Requires streaming data connection. v1 uses fixed quarterly schedule |
| Webhook notifications | v1 uses push + email. Webhooks for API integrations in v1.5 |
| Background data refresh (evidence store) | v1 acquires fresh data per run. Shared cache in v1.5 |

---

## Implementation Sequence

Based on dependencies, implement in this order:

```
Round 1: Foundation
  [11] PersistenceStore          ← everything depends on this
  [1]  GoalIntake                ← entry point, simple

Round 2: Planning pipeline
  [2]  DomainFramer              ← needs GoalIntake output
  [3]  ResearchSpecCompiler      ← needs DomainFramer output
  [5]  CandidateGenerator        ← needs ResearchSpec
  [4]  EvidencePlanner           ← needs Candidates
  [6]  ValidationPlanner         ← needs Evidence

Round 3: Execution
  [7]  ExecutionLayer.DataAcq    ← needs EvidencePlan
  [7]  ExecutionLayer.Backtest   ← needs ValidationPlan + data
  [7]  ExecutionLayer.Comparison ← needs TestResults

Round 4: Judgment
  [8]  AuditEngine               ← needs everything from Round 2–3
  [9]  RecommendationEngine      ← needs Audit results

Round 5: User-facing
  [10] ReportingEngine           ← needs Recommendation
  Pipeline Orchestrator          ← wires Rounds 1–5 together
  API endpoints                  ← exposes orchestrator to user

Round 6: Runtime
  [7]  ExecutionLayer.PaperRun   ← needs Approval
  [10] ReportingEngine.Monthly   ← needs PaperRunState
  [7]  ExecutionLayer.ReEval     ← needs existing pipeline
  Notification system            ← needs all runtime events
```

Each round is testable independently. Round 1–5 can be validated with a single end-to-end test: input a goal, get candidate cards.

---

**Role of this document**: This defines how data flows between modules, how the API is structured, how data is persisted, and how the audit trail works. Implementation of API endpoints, storage layer, and inter-module communication must conform to these specifications. If implementation reveals a flow that doesn't match this document, update this document before changing the flow.

---

**Fixes applied in this version**:
- Flow B: `confirmations` → `user_confirmations`, `stop_conditions` → `stop_conditions_reviewed` to match internal_schema.md §11 Approval Object field names (B-1)
- Flow E: `confirmations` → `user_confirmations` for same reason (B-1)
