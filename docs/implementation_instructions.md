# Give Me a DAY v1 — Implementation Instructions

**For**: Claude Code
**Purpose**: Build Give Me a DAY v1 from source of truth documents
**Language**: Python (backend), TypeScript + React (frontend)
**Status**: Ready for implementation

---

## 1. Implementation Purpose

Build a working v1 of Give Me a DAY: a validate-then-operate system that converts AI intelligence into real-world outcomes, starting with investment strategies.

The system receives a user's investment goal in natural language, internally generates/tests/compares/rejects candidate strategies using real public data, presents the 2 strongest survivors as cards for user approval, and upon approval operates the chosen strategy autonomously in Paper Run (simulated, no real money).

The user types a goal, waits 5–10 minutes, sees 2 candidate cards, approves one, and has a strategy running in daily simulation. Monthly reports are pushed. Quarterly re-evaluation runs automatically. Stop conditions halt the system when breached.


### Product thesis note (implementation guardrail)

- v1 is intentionally investment-first, but investment is the first domain pack, not the final product identity.
- Validation is the reality-conversion layer between ideas and results.
- Persisted run outcomes should be treated as reusable product knowledge to improve future candidate design, validation design, and rejection quality.
---

## 2. v1 Scope

### What v1 does

- Accepts natural-language investment goals (Japanese equities, US equities, daily frequency)
- Classifies goals into strategy archetypes (FACTOR, STAT_ARB, EVENT, MACRO, ML_SIGNAL, ALT_DATA, HYBRID)
- Generates 3–5 candidate strategies internally
- Acquires public daily data (Yahoo Finance, FRED, CFTC)
- Runs backtests, out-of-sample tests, walk-forward, regime-split, sensitivity analysis
- Performs statistical significance tests (t-test, bootstrap, multiple testing correction)
- Compares candidates across 6 axes
- Audits candidates across 10 categories with 48 issue patterns
- Rejects candidates that fail audit
- Presents 2 surviving candidates as cards (or 1, or 0 with explanation)
- Requires explicit user approval with risk confirmation before Paper Run starts
- Operates Paper Run: daily virtual portfolio updates, stop condition monitoring, anomaly detection
- Generates monthly reports in natural language
- Re-evaluates quarterly by re-running pipeline Steps 5–8 with fresh data
- Requires re-approval when recommendation changes or stop condition triggers

### Markets and data

- Japanese equities (TOPIX universe, Yahoo Finance JP)
- US equities (S&P 500 universe, Yahoo Finance US)
- Macro indicators (FRED: GDP, CPI, rates, VIX)
- CFTC Commitments of Traders
- Daily frequency only
- Max 20 years of history, max 500 instruments per universe

---

## 3. What v1 Does NOT Do

- No real-money execution (Paper Run only)
- No broker API integration
- No paid data sources
- No tick/intraday data
- No user-customizable stop conditions (system-defined, fixed)
- No analytics dashboard (status card + monthly report only)
- No multiple simultaneous strategies
- No cross-asset strategies
- No PDF export (Markdown only)
- No multi-user support (single user)
- No authentication system (v1 assumes single local user)
- No regulatory compliance advice
- No performance guarantees

---

## 4. Directory Structure

```
give-me-a-day/
├── README.md
├── docs/
│   ├── product_definition.md
│   ├── v1_boundary.md
│   ├── v1_output_spec.md
│   ├── internal_schema.md
│   ├── core_loop.md
│   ├── execution_layer.md
│   ├── technical_design.md
│   └── api_data_flow.md
│
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                        # FastAPI app entry point
│   │   ├── config.py                      # Environment config, constants
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                  # All API endpoints
│   │   │   ├── schemas.py                 # Pydantic models for API request/response
│   │   │   └── dependencies.py            # Shared dependencies (persistence, etc.)
│   │   │
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py            # Pipeline sequencer
│   │   │   ├── goal_intake.py             # Module 1
│   │   │   ├── domain_framer.py           # Module 2
│   │   │   ├── research_spec_compiler.py  # Module 3
│   │   │   ├── evidence_planner.py        # Module 4
│   │   │   ├── candidate_generator.py     # Module 5
│   │   │   └── validation_planner.py      # Module 6
│   │   │
│   │   ├── execution/
│   │   │   ├── __init__.py
│   │   │   ├── data_acquisition.py        # Public API clients
│   │   │   ├── data_quality.py            # 5-check quality assessment
│   │   │   ├── backtest_engine.py         # Vectorized backtester
│   │   │   ├── statistical_tests.py       # t-test, bootstrap, ADF, etc.
│   │   │   ├── comparison_engine.py       # Cross-candidate comparison
│   │   │   └── paper_run/
│   │   │       ├── __init__.py
│   │   │       ├── daily_cycle.py         # Daily Paper Run execution
│   │   │       ├── stop_conditions.py     # Stop condition checking
│   │   │       ├── anomaly_detection.py   # Signal anomaly detection
│   │   │       └── scheduler.py           # Cron-like scheduler for daily cycle
│   │   │
│   │   ├── judgment/
│   │   │   ├── __init__.py
│   │   │   ├── audit_engine.py            # Module 8: 10-category, 48-pattern audit
│   │   │   ├── audit_patterns/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── assumption.py          # ASM-01 to ASM-07
│   │   │   │   ├── evidence_gap.py        # EVD-01 to EVD-06
│   │   │   │   ├── leakage.py             # LKG-01 to LKG-07
│   │   │   │   ├── overfitting.py         # OVF-01 to OVF-06
│   │   │   │   ├── realism.py             # RLM-01 to RLM-07
│   │   │   │   ├── regime.py              # RGM-01 to RGM-05
│   │   │   │   ├── complexity.py          # CMP-01 to CMP-05
│   │   │   │   ├── observability.py       # OBS-01 to OBS-04
│   │   │   │   ├── cost.py                # CST-01 to CST-04
│   │   │   │   ├── recommendation_risk.py # RCR-01 to RCR-05
│   │   │   │   └── compound.py            # 5 compound patterns
│   │   │   ├── confidence.py              # FC-01 to FC-06
│   │   │   └── recommendation_engine.py   # Module 9
│   │   │
│   │   ├── reporting/
│   │   │   ├── __init__.py
│   │   │   ├── card_generator.py          # CandidateCard derivation
│   │   │   ├── presentation_generator.py  # PresentationContext
│   │   │   ├── monthly_report.py          # Monthly report generation
│   │   │   ├── markdown_export.py         # Markdown template rendering
│   │   │   ├── notification.py            # Push + email notification
│   │   │   └── term_translation.py        # Internal terms → plain Japanese
│   │   │
│   │   ├── persistence/
│   │   │   ├── __init__.py
│   │   │   ├── store.py                   # File-based persistence (JSON + Parquet)
│   │   │   ├── schema_validator.py        # Validates objects against internal_schema
│   │   │   ├── integrity_checker.py       # Cross-object referential integrity
│   │   │   └── audit_log.py              # JSONL audit event logging
│   │   │
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models.py                  # Pydantic models matching internal_schema
│   │   │   ├── archetype_templates.py     # Per-archetype claim/candidate templates
│   │   │   ├── evidence_taxonomy.py       # 7-category bias checklists, proxy rules
│   │   │   ├── audit_rubric.py            # Pattern definitions, severity logic
│   │   │   └── knowledge_base.py          # Known approaches, domain defaults
│   │   │
│   │   └── llm/
│   │       ├── __init__.py
│   │       ├── client.py                  # Anthropic API client wrapper
│   │       ├── prompts.py                 # All LLM prompt templates
│   │       └── fallbacks.py              # Template-based fallbacks when LLM unavailable
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_goal_intake.py
│   │   ├── test_domain_framer.py
│   │   ├── test_candidate_generator.py
│   │   ├── test_backtest_engine.py
│   │   ├── test_audit_engine.py
│   │   ├── test_recommendation_engine.py
│   │   ├── test_card_generator.py
│   │   ├── test_paper_run.py
│   │   ├── test_persistence.py
│   │   ├── test_pipeline_e2e.py           # End-to-end pipeline test
│   │   └── fixtures/
│   │       ├── sample_goals.json          # Test goal inputs
│   │       ├── sample_data/               # Small test datasets
│   │       └── expected_outputs/          # Expected pipeline outputs
│   │
│   └── data/                              # Runtime data directory
│       ├── runs/
│       ├── paper_runs/
│       ├── evidence/
│       └── audit_log/
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── api/
│   │   │   └── client.ts                  # API client (fetch wrapper)
│   │   ├── pages/
│   │   │   ├── InputPage.tsx              # S1: Goal input
│   │   │   ├── LoadingPage.tsx            # S2: Pipeline execution progress
│   │   │   ├── PresentationPage.tsx       # S3: 2-candidate cards
│   │   │   ├── ApprovalPage.tsx           # S4: Risk confirmation + approve
│   │   │   └── StatusPage.tsx             # S5: Paper Run status card
│   │   ├── components/
│   │   │   ├── CandidateCard.tsx          # Single candidate card
│   │   │   ├── ProgressIndicator.tsx      # 7-step progress
│   │   │   ├── StatusCard.tsx             # Paper Run status
│   │   │   ├── MonthlyReport.tsx          # Report display
│   │   │   └── RiskConfirmation.tsx       # Approval checkbox + button
│   │   └── types/
│   │       └── schema.ts                  # TypeScript types matching API responses
│   └── public/
│       └── index.html
│
└── scripts/
    ├── setup.sh                           # Install dependencies
    ├── run_dev.sh                         # Start backend + frontend
    ├── run_pipeline_test.sh               # Run e2e pipeline test
    └── seed_test_data.sh                  # Download sample data for testing
```

---

## 5. Data Model / Type Definition

### Backend: Pydantic models in `backend/src/domain/models.py`

Every object in `internal_schema.md` gets a Pydantic model. These are the single source of truth for data shapes in code.

```python
# Example structure (implement ALL 17 objects from internal_schema.md)

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class RiskPreference(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class UserIntent(BaseModel):
    run_id: str
    created_at: datetime
    raw_goal: str
    domain: str = "investment_research"
    user_goal_summary: str
    success_definition: str
    risk_preference: RiskPreference
    time_horizon_preference: str
    must_not_do: list[str] = []
    available_inputs: list[str] = []
    open_uncertainties: list[str] = []

# ... all 17 objects
```

### Frontend: TypeScript types in `frontend/src/types/schema.ts`

Only the API-exposed types (CandidateCard, PresentationContext, PaperRunState subset, MonthlyReport). NOT the full internal schema.

```typescript
// Only user-facing types
interface CandidateCard {
  candidate_id: string;
  label: "primary" | "alternative";
  display_name: string;
  summary: string;
  strategy_approach: string;
  expected_return_band: {
    low_pct: number;
    high_pct: number;
    basis: string;
    disclaimer: string;
  };
  estimated_max_loss: {
    low_pct: number;
    high_pct: number;
    basis: string;
  };
  confidence_level: "low" | "medium" | "high";
  confidence_reason: string;
  key_risks: string[];
  stop_conditions_headline: string;
}

// ... PresentationContext, RunStatus, PaperRunStatus, MonthlyReport
```

### Validation enforcement

Every Pydantic model write is validated automatically. Additional constraints enforced at application level:

- CandidateCard: all fields non-null, non-empty. `key_risks` has 2–3 items.
- Audit: `rejection_reason` minimum 3 sentences if `audit_status == "rejected"`
- Recommendation: `open_unknowns` non-empty, `critical_conditions` non-empty, `ranking_logic` ≥ 3 axes
- Approval: all `user_confirmations` must be `true`

---

## 6. Frontend

### Technology

- React 18 + TypeScript
- Vite for bundling
- TailwindCSS for styling
- No component library (custom components, minimal UI)
- No state management library (React state + context is sufficient for 5 pages)

### Pages (5 total)

| Page | Route | Purpose |
|------|-------|---------|
| InputPage | `/` | Single-screen goal input |
| LoadingPage | `/runs/{id}/loading` | Pipeline progress (polling) |
| PresentationPage | `/runs/{id}/result` | 2-candidate card display |
| ApprovalPage | `/runs/{id}/approve` | Risk confirmation + approve |
| StatusPage | `/paper-runs/{id}` | Paper Run status card |

### InputPage behavior

- Single textarea for goal (required)
- 1 text input for success criteria (optional)
- 2 dropdowns: risk tolerance (4 options), time horizon (5 options)
- Checkbox group for exclusions (4 options)
- "検証する →" button
- On submit: `POST /api/v1/runs` → redirect to LoadingPage

### LoadingPage behavior

- Poll `GET /api/v1/runs/{id}/status` every 3 seconds
- Display 7-step checklist with ✅/🔄/⬜ indicators
- Show estimated remaining time
- On completion: auto-redirect to PresentationPage
- On failure: show error message + "もう一度やる" button

### PresentationPage behavior

- Fetch `GET /api/v1/runs/{id}/result`
- Display 0, 1, or 2 CandidateCard components side by side
- Display PresentationContext below cards (validation_summary, expiry, rejection_headline, caveats)
- Each card has "この方向で進める →" button → navigates to ApprovalPage
- 0-card variant: show rejection explanation + 3 alternative directions + "別のアイデアで検証する →"
- "パッケージを保存" button → fetch `/api/v1/runs/{id}/export` → download .md file

### ApprovalPage behavior

- Display selected CandidateCard (read-only)
- Display key_risks (re-displayed)
- Display full stop condition list (4 conditions)
- Display re-evaluation schedule
- Display "Paper Run: 実際のお金は使いません" notice
- Virtual capital input (default ¥1,000,000)
- Checkbox: "☑ 上記のリスクと停止条件を確認しました"
- Button: "この方向で模擬運用を開始 →" (disabled until checkbox checked)
- On submit: `POST /api/v1/runs/{id}/approve` → redirect to StatusPage
- "やめて戻る" link → back to PresentationPage

### StatusPage behavior

- Fetch `GET /api/v1/paper-runs/{id}` on load and every 60 seconds
- Display single status card: 🟢🟡🔴⏸, current value, return %, stop condition proximity, next report, next re-eval
- "運用を停止する" button → `POST /api/v1/paper-runs/{id}/stop` → confirm dialog → refresh
- "月次レポートを見る" link → list of MonthlyReports
- If status = halted: show halt reason + "再承認して再開" button

### Design guidelines

- Minimal, clean UI. No decorative elements
- Japanese text as primary language
- Mobile-responsive (single-column on mobile)
- No animations except progress indicators
- No charts, graphs, or data visualizations in v1
- Error states: show plain-language error + retry action
- Color: 🟢 green = safe, 🟡 yellow = attention, 🔴 red = halted/rejected

---

## 7. Backend

### Technology

- Python 3.11+
- FastAPI for API server
- Pydantic v2 for data models
- Anthropic Python SDK for LLM calls
- yfinance for stock data
- fredapi for macro data
- numpy for vectorized backtest
- scipy + statsmodels for statistical tests
- pandas for data manipulation
- APScheduler for Paper Run daily scheduling
- No database (file-based persistence in v1)

### FastAPI app structure

```python
# backend/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router

app = FastAPI(title="Give Me a DAY", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.include_router(router, prefix="/api/v1")
```

### Configuration

```python
# backend/src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATA_DIR: str = "./data"
    ANTHROPIC_API_KEY: str
    FRED_API_KEY: str
    BACKTEST_TIMEOUT_SECONDS: int = 300
    PIPELINE_TIMEOUT_SECONDS: int = 700
    PAPER_RUN_SCHEDULE_HOUR: int = 16  # JST market close + 1hr
    DEFAULT_VIRTUAL_CAPITAL: int = 1_000_000
    DEFAULT_COMMISSION_BPS: int = 10
    DEFAULT_SPREAD_BPS: int = 10

    class Config:
        env_file = ".env"
```

### LLM usage

Claude API is used for:
- Goal summarization (GoalIntake)
- Domain classification (DomainFramer)
- Problem reframing (DomainFramer)
- Testable claims generation (DomainFramer)
- Candidate strategy generation (CandidateGenerator)
- Monthly report natural-language summary (ReportingEngine)

Every LLM call has a template-based fallback if the API is unavailable. Fallbacks produce lower-quality but structurally valid output.

---

## 8. API Endpoints

| Method | Path | Request Body | Response | Status |
|--------|------|-------------|----------|--------|
| `POST` | `/api/v1/runs` | `{goal, success_criteria?, risk?, time_horizon?, exclusions?}` | `{run_id, status_url}` | 202 |
| `GET` | `/api/v1/runs/{run_id}/status` | — | `{status, current_step, steps_completed, steps_total, estimated_remaining_seconds}` | 200 |
| `GET` | `/api/v1/runs/{run_id}/result` | — | `{candidate_cards[], presentation_context, approval_url}` | 200 |
| `GET` | `/api/v1/runs/{run_id}/export` | — | Markdown text | 200 |
| `POST` | `/api/v1/runs/{run_id}/approve` | `{candidate_id, user_confirmations, virtual_capital?}` | `{approval_id, paper_run_id, status_url}` | 201 |
| `GET` | `/api/v1/paper-runs/{pr_id}` | — | `{status, day_count, current_value, return_pct, safety_status, schedule}` | 200 |
| `POST` | `/api/v1/paper-runs/{pr_id}/stop` | — | `{status: "halted"}` | 200 |
| `POST` | `/api/v1/paper-runs/{pr_id}/re-approve` | `{candidate_id, user_confirmations}` | `{new_approval_id, status}` | 201 |
| `GET` | `/api/v1/paper-runs/{pr_id}/reports` | — | `MonthlyReport[]` | 200 |
| `GET` | `/api/v1/paper-runs/{pr_id}/reports/{report_id}` | — | `MonthlyReport` | 200 |

---

## 9. Persistence

### Storage: file-based JSON + Parquet

All data in `{DATA_DIR}/` directory. Structure defined in api_data_flow.md §6.

### Implementation rules

- Every write validates against Pydantic model before saving
- JSON files are pretty-printed (indent=2) for debuggability
- Parquet files use pyarrow engine
- PaperRunState.state.json is overwritten daily; previous state preserved as snapshot
- Audit log is append-only JSONL (one event per line)
- No file deletion in normal operation. Retention is managed by scheduled cleanup (v1.5)
- File locking: use `fcntl.flock` for concurrent access to Paper Run state (single user, but scheduler + API may collide)

### Key persistence operations

```python
class PersistenceStore:
    def save_run_object(self, run_id: str, object_type: str, data: BaseModel): ...
    def load_run_object(self, run_id: str, object_type: str) -> dict: ...
    def save_paper_run_snapshot(self, pr_id: str, date: str, state: PaperRunState): ...
    def load_paper_run_state(self, pr_id: str) -> PaperRunState: ...
    def append_audit_event(self, event: AuditEvent): ...
    def save_evidence_data(self, run_id: str, item_id: str, df: pd.DataFrame): ...
    def load_evidence_data(self, run_id: str, item_id: str) -> pd.DataFrame: ...
```

---

## 10. Report Generation

### CandidateCard generation

CandidateCard is a derived object. It is generated by `reporting/card_generator.py` from:
- `Candidate.name` → `display_name` (translate to plain Japanese, remove jargon)
- `Candidate.summary` → `summary` (shorten to 2 sentences, simplify)
- `TestResult` (backtest) → `expected_return_band` (25th/75th percentile of rolling returns)
- `TestResult` (backtest) → `estimated_max_loss` (avg/worst max drawdown across regimes)
- `Recommendation.confidence_label` → `confidence_level`
- `Audit.residual_risks[:3]` → `key_risks` (translate to plain language)

If TestResults are unavailable, use wider estimation ranges from `comparable_known_approaches` and add "データ検証未完了" caveat.

### Term translation

`reporting/term_translation.py` maintains a dictionary mapping internal terms to plain Japanese:

```python
TRANSLATIONS = {
    "candidate": "方向",
    "baseline": "基準案",
    "conservative": "堅実案",
    "exploratory": "挑戦案",
    "rejected": "棄却",
    "offline_backtest": "過去データでの検証",
    "out_of_sample": "手前のデータで作り、残りで試す検証",
    "walk_forward": "時間をずらしながらの検証",
    "regime_split": "相場環境ごとの検証",
    "sensitivity": "条件を変えたときの感度検証",
    "survivorship_bias": "生き残った銘柄だけで判断するリスク",
    "look_ahead_bias": "未来の情報を使ってしまうリスク",
    "overfitting": "データに合わせすぎること",
    "sharpe_ratio": "リスクあたりのリターンの効率",
    "max_drawdown": "最大損失（ピークから底まで）",
    # ... 40+ terms
}
```

Forbidden terms in user-facing output: Sharpe, Sortino, Calmar, alpha, beta, drawdown (use translations instead). `reporting/card_generator.py` scans generated text and replaces any forbidden terms.

### Monthly report

Generated by `reporting/monthly_report.py`. Uses LLM to produce 3–5 sentence natural-language summary from numerical data. Template:

```
先月は{monthly_return_pct}%のリターンでした。
{benchmark_name}の{benchmark_return_pct}%と比較して{comparison}。
停止条件には{safety_status}。
現在の累積リターンは開始から{cumulative_return_pct}%です。
{next_action}
```

LLM fills in natural connecting language. If LLM unavailable, template is used directly with variable substitution.

### Markdown export

`reporting/markdown_export.py` renders the template defined in v1_output_spec.md using CandidateCard + PresentationContext data.

---

## 11. Task Breakdown

### Round 1: Foundation (Target: days 1–3)

| Task | File(s) | Acceptance |
|------|---------|-----------|
| 1.1 Project scaffold | All directories, pyproject.toml, package.json | `pip install -e .` succeeds, `npm install` succeeds |
| 1.2 Pydantic models | `domain/models.py` | All 17 schema objects defined. `UserIntent(**sample_data)` validates |
| 1.3 PersistenceStore | `persistence/store.py` | save + load round-trips for all object types. Schema validation on write |
| 1.4 Audit event logger | `persistence/audit_log.py` | Events append to JSONL. Read back and parse |
| 1.5 Config + env | `config.py`, `.env.example` | Settings load from env. API keys configurable |
| 1.6 FastAPI skeleton | `main.py`, `api/routes.py` | Server starts. `GET /api/v1/health` returns 200 |

### Round 2: Planning Pipeline (Target: days 4–8)

| Task | File(s) | Acceptance |
|------|---------|-----------|
| 2.1 GoalIntake | `pipeline/goal_intake.py` | Input "日本株でモメンタム戦略を試したい" → valid UserIntent with domain=investment_research |
| 2.2 LLM client | `llm/client.py`, `llm/prompts.py`, `llm/fallbacks.py` | Claude API call succeeds. Fallback produces valid output when API key is empty |
| 2.3 DomainFramer | `pipeline/domain_framer.py` | UserIntent → DomainFrame with archetype=FACTOR, ≥3 testable_claims, regime_dependencies non-empty |
| 2.4 Archetype templates | `domain/archetype_templates.py` | Templates for all 7 archetypes. Each produces ≥3 claims with falsification_conditions |
| 2.5 ResearchSpecCompiler | `pipeline/research_spec_compiler.py` | UserIntent + DomainFrame → ResearchSpec with minimum_evidence_standard derived mechanically |
| 2.6 CandidateGenerator | `pipeline/candidate_generator.py` | ResearchSpec + DomainFrame → 3–5 Candidates (baseline + conservative + exploratory). Diversity check passes |
| 2.7 EvidencePlanner | `pipeline/evidence_planner.py` | ResearchSpec + Candidates → EvidencePlan per candidate with coverage_metrics |
| 2.8 Evidence taxonomy | `domain/evidence_taxonomy.py` | 7-category bias checklists. Proxy rules. Bias scan function |
| 2.9 ValidationPlanner | `pipeline/validation_planner.py` | ResearchSpec + Candidates + Evidence → ValidationPlan per candidate. Every test has ≥1 failure_condition |

### Round 3: Execution (Target: days 9–14)

| Task | File(s) | Acceptance |
|------|---------|-----------|
| 3.1 Data acquisition | `execution/data_acquisition.py` | Fetch 5 years of TOPIX daily OHLCV via yfinance. Fetch VIX from FRED. Return DataFrames |
| 3.2 Data quality checker | `execution/data_quality.py` | Run 5 checks (completeness, consistency, temporal, survivorship, PIT) on acquired data. Produce DataQualityReport |
| 3.3 Backtest engine | `execution/backtest_engine.py` | Given a FACTOR candidate + daily OHLCV → compute monthly-rebalance backtest → return time series of net returns |
| 3.4 Universe builder | Within backtest_engine | Build TOPIX universe from constituent data. Handle survivorship (best-effort with free data) |
| 3.5 Cost model | Within backtest_engine | Apply commission 10bps + spread 10bps. Compute gross vs net returns |
| 3.6 Statistical tests | `execution/statistical_tests.py` | t-test, bootstrap p-value, Sharpe significance, in-sample vs OOS comparison, multiple testing correction |
| 3.7 Out-of-sample test | Within statistical_tests or backtest_engine | 70/30 split. Run backtest on both. Compare Sharpe in-sample vs OOS |
| 3.8 Walk-forward test | Within backtest_engine | 3-year train / 1-year step. Produce per-window metrics |
| 3.9 Regime split test | Within backtest_engine | Classify periods into bull/bear/high_vol/low_vol using VIX + index trend. Backtest per regime |
| 3.10 Sensitivity test | Within backtest_engine | Grid over cost assumptions (10/20/30/50 bps). Grid over lookback period (6/9/12/18 months) |
| 3.11 Comparison engine | `execution/comparison_engine.py` | Normalize all candidate metrics. Statistical significance of differences. Ranking per axis |

### Round 4: Judgment (Target: days 15–19)

| Task | File(s) | Acceptance |
|------|---------|-----------|
| 4.1 Audit pattern scanners | `judgment/audit_patterns/*.py` | Each file implements scan functions for its category. Returns list of AuditIssue objects |
| 4.2 Tier 1 patterns | Across audit_patterns/ | ASM-01,02,04; EVD-01,05; LKG-01,02,03; OVF-01,06; RLM-01,02; RGM-01 — all implemented |
| 4.3 Compound patterns | `judgment/audit_patterns/compound.py` | 5 compound patterns detect cross-category combinations |
| 4.4 Confidence calculator | `judgment/confidence.py` | FC-02 mechanical rules. Input: coverage%, issue counts → output: low/medium/high |
| 4.5 AuditEngine | `judgment/audit_engine.py` | Run all pattern scanners in 4 phases. Determine audit_status. Build rejection_reason if rejected. FC-01 zero-issue check |
| 4.6 Execution-informed audit | Within audit_engine | When TestResults exist, adjust severity per execution_layer.md rules |
| 4.7 RecommendationEngine | `judgment/recommendation_engine.py` | Select best + runner-up. 6-axis ranking_logic. Derive conditions, unknowns, expiry. Confidence from FC-02 |
| 4.8 All-rejection loop | Within pipeline/orchestrator.py | If all rejected, re-generate candidates once with rejection constraints. If still all rejected, output null recommendation |

### Round 5: User-Facing (Target: days 20–24)

| Task | File(s) | Acceptance |
|------|---------|-----------|
| 5.1 Card generator | `reporting/card_generator.py` | Recommendation + Candidates + Audits + TestResults → 0–2 CandidateCards. All fields non-null. No jargon in output |
| 5.2 Term translation | `reporting/term_translation.py` | 40+ term dictionary. Scan-and-replace function. No Sharpe/drawdown/alpha in user text |
| 5.3 Presentation generator | `reporting/presentation_generator.py` | Produce PresentationContext with validation_summary, expiry, rejection_headline, caveats |
| 5.4 Markdown export | `reporting/markdown_export.py` | Render template from v1_output_spec.md. Downloadable .md file |
| 5.5 Pipeline orchestrator | `pipeline/orchestrator.py` | Wire all modules. Handle errors per api_data_flow.md error propagation table. Timeout budget enforcement |
| 5.6 API endpoints | `api/routes.py` | All 10 endpoints. POST /runs triggers background pipeline. GET /status returns progress. GET /result returns cards |
| 5.7 Frontend: InputPage | `frontend/src/pages/InputPage.tsx` | Goal textarea + optional fields + submit. POST to API |
| 5.8 Frontend: LoadingPage | `frontend/src/pages/LoadingPage.tsx` | Poll status every 3s. 7-step checklist. Auto-redirect on completion |
| 5.9 Frontend: PresentationPage | `frontend/src/pages/PresentationPage.tsx` | Display 0/1/2 cards. Selection buttons. Export button |
| 5.10 Frontend: ApprovalPage | `frontend/src/pages/ApprovalPage.tsx` | Risk display. Checkbox. Gated approve button. POST approval |
| 5.11 E2E test | `tests/test_pipeline_e2e.py` | Input "日本株で12ヶ月モメンタム戦略を検証したい" → pipeline completes → 2 cards generated → approval creates PaperRunState |

### Round 6: Paper Run Runtime (Target: days 25–30)

| Task | File(s) | Acceptance |
|------|---------|-----------|
| 6.1 Daily cycle | `execution/paper_run/daily_cycle.py` | Fetch data → calculate signals → update portfolio → check stops → save snapshot |
| 6.2 Stop conditions | `execution/paper_run/stop_conditions.py` | SC-01 (drawdown -20%), SC-02 (3-month underperf), SC-03 (signal 3σ), SC-04 (data fail 3 days). Auto-halt on breach |
| 6.3 Anomaly detection | `execution/paper_run/anomaly_detection.py` | Track signal distribution. Flag 3σ deviations |
| 6.4 Scheduler | `execution/paper_run/scheduler.py` | Register daily cycle for active Paper Runs. APScheduler or cron integration |
| 6.5 Monthly report gen | `reporting/monthly_report.py` | Aggregate month's snapshots → natural language summary → MonthlyReport object |
| 6.6 Notification stub | `reporting/notification.py` | v1: log notifications to file. Email integration is v1.5. Push is v1.5 |
| 6.7 Re-evaluation runner | Within daily_cycle or separate scheduler | Quarterly: re-run Steps 5–8. Compare result to current candidate. Produce ReEvaluationResult |
| 6.8 Frontend: StatusPage | `frontend/src/pages/StatusPage.tsx` | Status card. Stop button. Report list link |
| 6.9 Re-approval flow | API + frontend | If re-eval recommends change → new PresentationPage → ApprovalPage |
| 6.10 Paper Run E2E test | `tests/test_paper_run.py` | Create Paper Run → simulate 5 daily cycles → verify snapshots saved → verify stop condition check ran |

---

## 12. Acceptance Criteria

### Pipeline E2E

Given input: `"日本株で12ヶ月モメンタム戦略を検証したい"`

Expected:
1. UserIntent created with domain = "investment_research"
2. DomainFrame created with archetype = "FACTOR"
3. ≥ 3 candidates generated (baseline + conservative + exploratory)
4. Public data acquired (OHLCV + at least 1 macro indicator)
5. Backtests executed for all candidates
6. Statistical tests run (at least t-test + OOS comparison)
7. ≥ 1 candidate audited and rejected OR audited with warnings
8. Recommendation produced with confidence_label ∈ {low, medium}
9. 1 or 2 CandidateCards generated with all fields non-null
10. PresentationContext includes validation_summary with correct counts
11. Markdown export renders without errors
12. Total pipeline time ≤ 10 minutes

### Approval + Paper Run

Given: pipeline completed with 2 candidates, user selects Primary:
1. Approval requires all 3 confirmations = true
2. PaperRunState created with status = "running"
3. Daily cycle runs without error for simulated 5-day period
4. Stop conditions are checked each day
5. Snapshot saved each day
6. If drawdown exceeds -20%: status changes to "halted", halt_history updated

### Audit quality

Across 10 test runs with diverse goals:
1. At least 1 run produces 0-candidate result (all rejected)
2. No run produces 0 audit issues (FC-01 catches this)
3. confidence_label = "high" appears in ≤ 1 of 10 runs
4. Every rejected candidate has rejection_reason ≥ 3 sentences
5. Every passed candidate has surviving_assumptions non-empty

### Card quality

For every generated CandidateCard:
1. No forbidden terms (Sharpe, Sortino, drawdown, alpha, beta) in any string field
2. display_name is in Japanese
3. summary ≤ 2 sentences
4. key_risks has 2–3 items
5. expected_return_band.disclaimer is present
6. stop_conditions_headline is non-empty

---

## 13. Implementation Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| LLM generates low-quality DomainFrame or candidates | High | Test with 10+ diverse goals before launch. Fallback templates for each archetype. Manual quality review of first 20 outputs |
| Yahoo Finance API rate limits or blocks | High | Implement retry with exponential backoff. Cache acquired data in evidence/ directory. Fall back to planning-only mode if all acquisition fails |
| Backtest engine produces incorrect results (e.g., look-ahead bias in implementation) | Critical | Unit test every data access in backtest engine. Verify signal generation timestamp < data timestamp. Compare results against known published factor returns |
| Audit is too lenient (all candidates pass) | High | Test with deliberately weak candidates (e.g., random signal). Verify rejection. FC-01 catches zero-issue audits |
| Audit is too strict (no candidates ever pass) | High | Test with known-good strategies (12-month momentum on S&P 500). Verify at least 1 passes. Adjust severity thresholds if needed |
| Paper Run scheduler fails silently | Medium | Health check: if no snapshot saved for 2 trading days, alert. Daily cycle logs every execution (success or failure) |
| User inputs non-investment goal that passes domain check | Medium | Audit recommendation_risk (RCR-01) catches goals that produce nonsensical recommendations. Add more negative examples to domain classifier |
| Pipeline exceeds 10-minute timeout | Medium | Monitor per-step latency. Most likely bottleneck: data acquisition (API latency) or backtest (large universe). Reduce universe size if timeout approaches |
| Monthly report contains misleading language | Medium | LLM-generated text is scanned for forbidden terms. Template fallback ensures minimum quality. Review first 5 reports manually |
| Parquet/JSON corruption in persistence | Low | Copy-on-write for critical files. Daily backup for Paper Run state. Schema validation on every read |

---

## Reference Documents

Implementation must conform to these documents (in priority order):

1. `product_definition.md` — What the product is and is not
2. `v1_boundary.md` — What v1 includes and excludes
3. `v1_output_spec.md` — What the user receives (candidate cards, approval, Paper Run)
4. `internal_schema.md` — All data structures (17 objects)
5. `core_loop.md` — Processing flow (12 steps)
6. `execution_layer.md` — Backtest engine + Paper Run engine
7. `technical_design.md` — Module responsibilities and failure modes
8. `api_data_flow.md` — API endpoints, persistence, audit trail

If implementation conflicts with any of these documents, the document takes precedence. Update the document before changing the implementation.

---

**Fixes applied in this version**:
- §8 API table: approve endpoint request body `confirmations` → `user_confirmations` to match internal_schema.md §11 (B-1)
- §8 API table: re-approve endpoint request body `confirmations` → `user_confirmations` for same reason (B-1)
