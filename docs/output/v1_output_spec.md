# v1 Output Specification

## What "output" means in this product

Give Me a DAY does not output a document. It outputs a **running system**.

The user's journey has three output moments:

1. **Candidate Presentation**: The system shows 2 validated candidates for the user to choose from
2. **Approval Confirmation**: The system confirms what the user approved and under what conditions
3. **Ongoing Runtime**: The system operates the strategy, reports results, and re-evaluates

All three are outputs. The traditional concept of an "output package" or "recommendation report" maps only to moment 1 — and even then, the output is not a report but a pair of candidate cards designed for an approval decision, not for analysis.

---

## Output Moment 1: Candidate Presentation

### Purpose

Show the user what survived internal validation. Enable an approval decision in under 2 minutes. Do not enable or require analysis.

### Structure

The presentation consists of:
- 2 candidate cards (or 1, or 0 with explanation)
- Presentation context (validation summary, expiry, rejection headline, caveats)

### Candidate Card

Each candidate card contains exactly these fields:

```jsonc
{
  // ── Identity ──
  "candidate_id": "string",
  "label": "primary | alternative",
  "display_name": "string",               // "12ヶ月モメンタム × 等ウェイト" — no jargon

  // ── What it does ──
  "summary": "string",                    // Max 2 sentences. Plain language.
                                           // "過去12ヶ月の株価の勢いが強い銘柄に投資する戦略。
                                           //  月に1回、銘柄を入れ替えます。"

  "strategy_approach": "string",          // 1 sentence, even simpler.
                                           // "株価の勢いに乗る"

  // ── What to expect ──
  "expected_return_band": {
    "low_pct": "number",                   // Conservative annualized estimate
    "high_pct": "number",                  // Optimistic annualized estimate
    "basis": "string",                     // "過去20年のバックテスト（コスト控除後）"
    "disclaimer": "過去の実績は将来の成果を保証しません"
  },

  "estimated_max_loss": {
    "low_pct": "number",                   // Less severe max drawdown estimate
    "high_pct": "number",                  // More severe max drawdown estimate
    "basis": "string"
  },

  // ── How much to trust it ──
  "confidence_level": "low | medium | high",
  "confidence_reason": "string",           // 1 sentence.
                                           // "過去データでは有効だが、直近5年は弱まっている"

  // ── What can go wrong ──
  "key_risks": ["string"],                // 2–3 items. Plain language.
                                           // ["直近5年は効果が弱い",
                                           //  "下落相場ではマイナスになる可能性がある"]

  // ── What protects you ──
  "stop_conditions_headline": "string"    // 1 sentence.
                                           // "損失が-20%に達した場合、自動的に停止します"
}
```

**Every field is mandatory.** A candidate card with any missing field is invalid and must not be presented.

**No other fields are shown to the user.** The internal pipeline generates hundreds of data points per candidate. The card shows 8 fields. This compression is intentional — the user's job is to approve or reject, not to analyze.

### Presentation Context

Shown alongside the candidate cards:

```jsonc
{
  "run_id": "string",
  "created_at": "ISO-8601",

  // ── What the system did ──
  "validation_summary": "string",          // "5方向を検討、3方向を棄却、6種の検証を実施"
                                            // Always 1 sentence. Shows that serious work happened.

  // ── When to revisit ──
  "recommendation_expiry": "string",       // "3ヶ月後に自動で再評価します"

  // ── What was rejected ──
  "rejection_headline": "string | null",   // "3方向を棄却。主な理由: 過学習の疑い"
                                            // 1 sentence. null only if nothing was rejected (rare).

  // ── Limitations ──
  "caveats": ["string"],                   // Each 1 sentence. Data quality limitations.
                                            // ["無料データを使用しており、精度に限界があります",
                                            //  "上場廃止銘柄を含まないため、結果が楽観的な可能性があります"]

  // ── How many survived ──
  "candidates_evaluated": "integer",
  "candidates_rejected": "integer",
  "candidates_presented": "integer"        // 2, 1, or 0
}
```

### Presentation Variations

**2 candidates survive (normal case)**:
- Primary card (⭐) and Alternative card (🔄) side by side
- Each has "この方向で進める →" button
- Below cards: validation_summary, recommendation_expiry, rejection_headline, caveats

**1 candidate survives**:
- Primary card only
- Message: "代替候補は検証基準を満たしませんでした"

**0 candidates survive**:
- No cards
- Rejection headline with expanded explanation (3–5 sentences: what was tried, why it all failed)
- "次に試す価値がある方向" — 3 concrete alternative directions to try
- "別のアイデアで検証する →" button

### What the Candidate Presentation does NOT contain

| Excluded | Why |
|---------|-----|
| Sharpe ratio, Sortino, Calmar, information ratio | Metrics require expertise to interpret. Return band and max loss band are the user-facing translation |
| Backtest equity curve | Charts invite analysis. The card is for decision, not analysis |
| Per-test pass/fail table | Internal quality control. Reflected in confidence_level |
| Candidate comparison table | System has already compared and decided which 2 to present |
| Audit issue list | Internal audit trail. Reflected in key_risks |
| Evidence coverage percentage | Internal data quality metric. Reflected in confidence_level and caveats |
| DomainFrame, ResearchSpec, testable_claims | Internal pipeline state |
| Detailed rejection reasons per candidate | rejection_headline provides the summary. Details are internal |
| Architecture outline of each strategy | Implementation detail. User approved what the strategy does, not how it's built |
| Next steps checklist | The "next step" is approval. After approval, the system handles everything |

---

## Output Moment 2: Approval Confirmation

### Purpose

Record what the user approved, under what conditions, and with what safety mechanisms. This is both a user-facing confirmation and an internal contract that defines the runtime's operating boundaries.

### Approval Object

```jsonc
{
  "approval_id": "string",
  "run_id": "string",
  "candidate_id": "string",
  "approved_at": "ISO-8601",

  // ── What the user confirmed ──
  "user_confirmations": {
    "risks_reviewed": true,
    "stop_conditions_reviewed": true,
    "paper_run_understood": true             // v1: user confirmed no real money
  },

  // ── Operating parameters ──
  "runtime_config": {
    "initial_virtual_capital": "number",     // User-set. Default ¥1,000,000
    "currency": "JPY | USD",
    "rebalance_frequency": "monthly",        // v1 fixed
    "cost_model": {
      "commission_bps": 10,                  // v1 fixed
      "spread_bps": 10                       // v1 fixed
    },
    "execution_timing": "T+1_open"           // v1 fixed
  },

  // ── Safety mechanisms ──
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

  // ── Lifecycle rules ──
  "re_evaluation": {
    "monthly_report": true,
    "quarterly_full_re_evaluation": true,
    "re_evaluation_triggers": [
      "stop_condition_hit",
      "market_regime_change_detected",
      "user_requested"
    ]
  },

  "re_approval_required": [
    "candidate change recommended by re-evaluation",
    "resume after stop condition halt",
    "transition to real execution (v1.5)"
  ]
}
```

### Approval Screen Required Elements

| Element | Purpose |
|---------|---------|
| Selected candidate card (re-displayed) | Confirm exactly what is being approved |
| Key risks (re-displayed from card) | Ensure risk awareness immediately before commitment |
| Full stop condition list (all 4 conditions) | Show safety mechanisms |
| Re-evaluation schedule ("monthly report, quarterly strategy review") | Show this is not fire-and-forget |
| "Paper Run: 実際のお金は使いません" notice | v1 clarity |
| "☑ 上記のリスクと停止条件を確認しました" checkbox | Explicit acknowledgment gate |
| "この方向で模擬運用を開始 →" button (disabled until checkbox) | Gated action |
| "やめて戻る" link | Escape |

---

## Output Moment 3: Ongoing Runtime

### Purpose

Keep the user informed of the strategy's performance and safety status without requiring daily attention. The user's ongoing time commitment should be approximately 1 minute per month.

### Paper Run State

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
    "any_breached": "boolean",
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
  }
}
```

### Status Card (user-facing)

The user sees a single status card when they open the app. Not a dashboard. Not multiple charts. One card.

| Field | Source |
|-------|--------|
| Status light: 🟢 Running / 🟡 Attention / 🔴 Halted / ⏸ Re-evaluating | paper_run.status |
| Strategy name | candidate.display_name |
| Day count | current_snapshot.day_count |
| Current value + return | current_snapshot.virtual_capital_current + total_return_pct |
| Stop condition status | "すべて正常" or "⚠ 最大損失に接近中 (-16%)" | safety_status |
| Next report | schedule.next_monthly_report |
| Next re-evaluation | schedule.next_quarterly_re_evaluation |
| "運用を停止する" button | Always available |

**Status card does NOT show**: daily return chart, position list, trade history, performance vs benchmark chart, Sharpe or other metrics. These belong to v1.5 optional detail mode.

### Monthly Report

```jsonc
{
  "report_id": "string",
  "paper_run_id": "string",
  "period": { "start": "ISO-8601", "end": "ISO-8601" },

  "summary": "string",
  // Natural language. 3–5 sentences.
  // "先月は+1.2%のリターンでした。TOPIXの+0.8%を上回りました。
  //  停止条件にはいずれも到達していません。
  //  現在の累積リターンは開始から+2.4%です。
  //  来月も引き続き模擬運用を継続します。"

  "numbers": {
    "monthly_return_pct": "number",
    "benchmark_return_pct": "number",
    "cumulative_return_pct": "number",
    "current_drawdown_pct": "number",
    "positions_count": "integer",
    "trades_this_month": "integer"
  },

  "safety_note": "string",
  // "すべての停止条件から十分な距離があります"
  // or "最大損失が-16%に達しており、停止条件(-20%)に接近中です"

  "next": "string"
  // "引き続き模擬運用を継続します。次回レポートは5月16日です。"
  // or "来月、四半期の戦略再評価を実施します。"
}
```

**Monthly report is sent to the user (push + email). Not pulled.** The user does not need to log in to see it.

### Quarterly Re-evaluation

The system re-runs Core Loop Steps 5–8 with the most recent data. Three possible outcomes:

| Outcome | What user sees | User action required |
|---------|---------------|---------------------|
| Continue | "戦略を再評価しました。現行の方向で継続します。" | None. Automatic continuation |
| Change | "再評価の結果、別の方向を推奨します。確認が必要です。" + New 2-candidate presentation | Re-approval (S3 → S4 flow again) |
| Stop | "現在の市場環境では推奨できる方向がありません。運用を停止しました。" | Paper Run stops. User can start new run |

### Halt Event

When a stop condition is breached:

1. Paper Run halts immediately (no more trades)
2. User is notified within 1 hour (push + email)
3. Notification includes: which condition was hit, current state, what happens next
4. Resume requires re-approval (same flow as initial approval)

---

## Notifications

| Trigger | Message | Urgency | Timing |
|---------|---------|---------|--------|
| Monthly report | "先月の運用レポートが完成しました" | Normal | Within 3 days of month end |
| Stop condition approaching | "損失が-15%に達しました。停止条件(-20%)に接近中です" | High | Real-time |
| Stop condition hit | "停止条件に到達したため、模擬運用を停止しました" | Urgent | Within 1 hour |
| Re-evaluation complete (continue) | "戦略の再評価が完了しました。継続します" | Normal | Upon completion |
| Re-evaluation complete (change) | "別の方向を推奨します。確認が必要です" | High | Upon completion |
| Anomaly detected | "異常を検出したため、一時停止しました" | Urgent | Within 1 hour |

**Normal time: 1 notification per month (report).**
The user should not be trained to check the app daily. Monthly is enough when things are running normally.

---

## Markdown Export

"パッケージを保存" button on the Candidate Presentation screen exports the following:

```markdown
# Give Me a DAY — 検証結果

**ゴール**: {user's raw goal}
**検証日**: {date}
**信頼度**: {confidence level in Japanese}

## おすすめの方向

**{display_name}** ⭐ 推奨

{summary}

期待リターン: 年率 {low}〜{high}%（{basis}）
想定最大損失: {low}〜{high}%
{disclaimer}

### 主なリスク
{key_risks as bullet list}

### 停止条件
{stop_conditions_headline}

---

## 代替の方向

**{alt display_name}** 🔄 代替

{alt summary}

{same structure as above}

---

## 検証の概要

{validation_summary}
{rejection_headline}

## 注意事項

{caveats as bullet list}

## 有効期限

{recommendation_expiry}

---
*Give Me a DAY v1 により生成*
```

---

## Output Validation Rules

### Candidate Presentation rules

| ID | Rule |
|----|------|
| CP-01 | Presented candidates have audit_status ∈ {passed, passed_with_warnings} |
| CP-02 | Primary and Alternative are different candidates with different candidate_types |
| CP-03 | expected_return_band includes disclaimer |
| CP-04 | key_risks has 2–3 items per candidate |
| CP-05 | stop_conditions_headline is non-empty per candidate |
| CP-06 | confidence_level is mechanically calculated, not manually set |
| CP-07 | validation_summary includes candidate count, rejection count, test count |
| CP-08 | recommendation_expiry is non-empty |
| CP-09 | 0-candidate case includes rejection reasons + "next directions" (min 3) |
| CP-10 | All candidate card fields are non-null and non-empty |

### Approval rules

| ID | Rule |
|----|------|
| AP-01 | Approval requires risks_reviewed = true |
| AP-02 | Approval requires stop_conditions_reviewed = true |
| AP-03 | Approval requires paper_run_understood = true (v1) |
| AP-04 | stop_conditions array has ≥ 3 conditions |
| AP-05 | re_approval_required list is non-empty |

### Runtime rules

| ID | Rule |
|----|------|
| RT-01 | Stop conditions checked every trading day |
| RT-02 | Halt is automatic and immediate on breach |
| RT-03 | User notification within 1 hour of halt |
| RT-04 | Resume after halt requires re-approval |
| RT-05 | Monthly report generated within 3 days of month end |
| RT-06 | Quarterly re-evaluation runs Core Loop Steps 5–8 |
| RT-07 | Candidate change from re-evaluation requires re-approval |
| RT-08 | 0-candidate re-evaluation result halts Paper Run |

---

**Role of this document**: This defines exactly what the user receives from Give Me a DAY — not as a report to read, but as a running system to approve and monitor. It specifies the schemas, display rules, and validation rules for each output moment. Implementation of user-facing screens, API responses, and notification systems must conform to these definitions.
