# ops/prompts/owner_report.md

## Purpose
毎朝 Haruki が30秒で読める brief を生成するためのプロンプト。
「市場反応と内部状態のズレ」にフォーカスする。

---

## Input
- `docs/reports/daily/YYYY-MM-DD.md`（前日生成）
- `docs/marketing/logs/` の直近 1〜2 本
- `docs/marketing/weekly_kpi/` の最新版
- `OPEN_LOOPS.md`（High 優先度のみ）

---

## Prompt

```
以下のドキュメントを読んで、Haruki 向けの朝 brief を生成してください。

制約:
- 5行以内
- 「今日最重要な1つ」を先頭に
- 数字があれば使う。なければ「UNKNOWN」と書く
- 良い話より問題点を先に書く
- 「〜です。〜ます。」の丁寧語禁止。箇条書きで断定的に書く

フォーマット:
【今日の最重要】...（1行）
【build】... （success / fail + 要点）
【drift】... （none / weak signal / concern + 要点）
【マーケ】... （none / weak signal / concern + 要点）
【次の1手】...（今日中にやるべきこと）
```

---

## Sample Output

```
【今日の最重要】backend pytest 2件 fail — test_backtest_engine.py の assertion error
【build】frontend ✅ / backend ❌ (2 tests failed)
【drift】weak signal — docs/architecture に companion_ai の更新が反映されていない
【マーケ】none — 施策ログ未更新（3日ぶり）
【次の1手】test_backtest_engine.py の失敗原因を確認して修正 PR を出す
```
