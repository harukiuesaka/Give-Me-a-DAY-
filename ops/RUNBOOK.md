# ops/RUNBOOK.md — Give Me a DAY Ops Runbook

**対象**: daily report 生成ループを初めて動かす人（Human または CEO AI）  
**前提**: PR #6〜#14 が全て main に merge 済み

---

## 1. 必要な外部サービス

| サービス | 目的 | 必須？ |
|---------|------|--------|
| OpenRouter または Anthropic API | LLM による report 生成 | **必須**（どちらか1つ） |
| Supabase | 実行ログ永続化 | オプション |
| Railway | 朝 cron 自動実行 | オプション（ローカル手動でも可） |
| GitHub PAT | report を repo に push | オプション（ローカル確認のみなら不要） |

---

## 2. 初回セットアップ（コピペ実行可）

### Step 1: リポジトリを clone

```bash
git clone https://github.com/haruki121731-del/Give-Me-a-DAY-.git
cd Give-Me-a-DAY-
```

### Step 2: 環境変数を設定

```bash
cp .env.ops.example .env.ops
# .env.ops を編集して API キーを入力
nano .env.ops   # または好みのエディタ
source .env.ops
```

### Step 3: preflight チェック（secrets が正しく設定されたか確認）

```bash
bash ops/run.sh --check-only
```

**期待される出力:**
```
✅ LLM via OpenRouter (OPENROUTER_API_KEY)
✅ Supabase URL (SUPABASE_URL)
✅ ...
Preflight: ✅ all checks passed
```

### Step 4: dry-run（LLM を呼ばずにデータ収集のみ確認）

```bash
bash ops/run.sh --dry-run
```

**期待される出力:**
```
1. build check...    ✅ done
2. drift check...    ✅ done
3. marketing health... ✅ done
4. [DRY RUN] skipping LLM call — writing data-only report
Report: docs/reports/daily/YYYY-MM-DD.md
```

### Step 5: 本番実行（LLM report 生成 + git push）

```bash
bash ops/run.sh
```

**期待される出力:**
```
✅ LLM via OpenRouter (or Anthropic)
1. build check...    ✅ done
2. drift check...    ✅ done
3. marketing health... ✅ done
4. Calling LLM API...
   ✅ OpenRouter OK
5. Report written: docs/reports/daily/YYYY-MM-DD.md
6. Writing run state to Supabase... ✅ Supabase write OK
7. Committing and pushing report... ✅ pushed to main
Report: docs/reports/daily/YYYY-MM-DD.md
```

---

## 3. Railway cron 設定（朝 9:00 JST = 00:00 UTC）

1. [Railway](https://railway.app) で新規 project を作成
2. `New Service` → `Empty Service` を選択
3. `Settings` → `Deploy` タブ:
   - **Start Command**: `bash ops/run.sh --skip-commit`
   - **Schedule**: `0 0 * * *`（UTC 00:00 = JST 09:00）
4. `Variables` に以下を追加:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ANTHROPIC_API_KEY=sk-ant-...
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJ...
   GITHUB_TOKEN=ghp_...
   ```
5. `Deploy` → 手動で1回実行して確認

> **注意**: Railway cron は前の run が active の場合 skip される。  
> `generate_daily_report.sh` は必ず終了するので問題ない（確認済み）。

---

## 4. Supabase 初期設定

1. [Supabase](https://supabase.com) で新規 project を作成
2. `SQL Editor` を開く
3. `ops/schemas/run_state_schema.sql` の内容をコピペして実行
4. `Table Editor` → `run_logs` テーブルが作成されていることを確認
5. `Settings` → `API` から以下をコピーして `.env.ops` に設定:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` (secret) → `SUPABASE_SERVICE_ROLE_KEY`

---

## 5. 失敗時の対処

### OpenRouter 402 エラー（クレジット不足）

```
⚠️ OpenRouter failed: Insufficient credits
```

→ https://openrouter.ai/settings/credits でクレジット購入  
→ または `ANTHROPIC_API_KEY` を設定すれば自動 fallback

### Supabase insert 失敗

```
ERROR: HTTP 401 from Supabase
```

→ `SUPABASE_SERVICE_ROLE_KEY` が `anon` キーになっていないか確認  
→ Service role key は `eyJ...` で始まる長いトークン

### git push 失敗

```
⚠️ git push failed (report written locally)
```

→ `GITHUB_TOKEN` の権限が `repo` スコープを含むか確認  
→ report はローカルに生成済みなので手動で `git push origin main` も可

### dry-run で build check が失敗と表示される

→ VM 上で `npm` や `pytest` が使えない環境は想定内  
→ GitHub Actions CI が本番の build check として機能する  
→ dry-run の build check 失敗は report 生成をブロックしない

---

## 6. 成功の定義

毎朝 `docs/reports/daily/YYYY-MM-DD.md` が生成され、以下の3項目が埋まっていること:

- Build Failure（success / fail が明示されている）
- Architecture Drift 候補（none / weak signal / concern）
- マーケ反応（none / weak signal / concern）

これが揃えば Day 14 完了。
