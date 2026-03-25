#!/usr/bin/env python3
"""
LLM Quality Eval Runner — Give Me a DAY
Run: python3 scripts/eval_runner.py
Requires: ANTHROPIC_API_KEY env var, anthropic package installed

Loads cases from evals/llm_quality_cases.json
Calls claude-sonnet-4-20250514 with real prompts from backend/src/llm/prompts.py
Writes raw outputs to evals/results/run_YYYY-MM-DD.jsonl
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

# Ensure backend/src is importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend", "src"))

import anthropic

# ── constants ──────────────────────────────────────────────────────────────
# Use haiku — confirmed working in this workspace (Session 4 openhands E2E)
# claude-sonnet-4-20250514 is the pipeline model, but haiku is used for eval
# to control cost and because it has confirmed API access on this key.
MODEL = "claude-3-haiku-20240307"
TEMPERATURE = 0.3
MAX_TOKENS = 4096
PROMPT_VERSION = "1.0"
CASES_FILE = os.path.join(REPO_ROOT, "evals", "llm_quality_cases.json")
RESULTS_DIR = os.path.join(REPO_ROOT, "evals", "results")

# ── load prompts ────────────────────────────────────────────────────────────
from llm.prompts import (
    DOMAIN_FRAMING_SYSTEM,
    DOMAIN_FRAMING_USER,
    CANDIDATE_GENERATION_SYSTEM,
    CANDIDATE_GENERATION_USER,
    VALIDATION_PLANNING_SYSTEM,
    VALIDATION_PLANNING_USER,
)


def build_domain_framing_prompt(inp: dict) -> tuple[str, str]:
    user_prompt = DOMAIN_FRAMING_USER.format(
        raw_goal=inp["raw_goal"],
        goal_summary=inp["goal_summary"],
        success_definition=inp["success_definition"] or "指定なし",
        risk_preference=inp["risk_preference"],
        must_not_do=", ".join(inp["must_not_do"]) if inp["must_not_do"] else "なし",
    )
    return DOMAIN_FRAMING_SYSTEM, user_prompt


def build_candidate_generation_prompt(inp: dict) -> tuple[str, str]:
    user_prompt = CANDIDATE_GENERATION_USER.format(
        archetype=inp["archetype"],
        reframed_problem=inp["reframed_problem"],
        core_hypothesis=inp["core_hypothesis"],
        constraints=inp["constraints"],
        forbidden_behaviors=", ".join(inp["forbidden_behaviors"]) if inp["forbidden_behaviors"] else "なし",
    )
    # Append rejection constraints if present
    if inp.get("rejection_constraints"):
        user_prompt += "\n\n以下の方向性は前回棄却済みです。異なるアプローチを提案してください:\n"
        for rc in inp["rejection_constraints"]:
            user_prompt += f"- {rc}\n"
    return CANDIDATE_GENERATION_SYSTEM, user_prompt


def build_validation_planning_prompt(inp: dict) -> tuple[str, str]:
    user_prompt = VALIDATION_PLANNING_USER.format(
        candidate_name=inp["candidate_name"],
        candidate_type=inp["candidate_type"],
        archetype=inp["archetype"],
        coverage_percentage=inp["coverage_percentage"],
        gap_severity=inp["gap_severity"],
    )
    return VALIDATION_PLANNING_SYSTEM, user_prompt


def build_prompt(case: dict) -> tuple[str, str]:
    module = case["module"]
    inp = case["input"]
    if module == "DomainFramer":
        return build_domain_framing_prompt(inp)
    elif module == "CandidateGenerator":
        return build_candidate_generation_prompt(inp)
    elif module == "ValidationPlanner":
        return build_validation_planning_prompt(inp)
    else:
        raise ValueError(f"Unknown module: {module}")


def extract_json(text: str):
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return json.loads(text[start:end].strip())
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return json.loads(text[start:end].strip())
    for open_char, close_char in [("{", "}"), ("[", "]")]:
        if open_char in text:
            start = text.index(open_char)
            end = text.rindex(close_char) + 1
            return json.loads(text[start:end])
    raise json.JSONDecodeError("No JSON found", text, 0)


def run_case(client: anthropic.Anthropic, case: dict, run_date: str) -> dict:
    """Run one eval case and return a result record."""
    case_id = case["case_id"]
    module = case["module"]
    scenario_label = case["scenario_label"]
    print(f"  [{case_id}] {scenario_label} ...", end=" ", flush=True)

    try:
        system_prompt, user_prompt = build_prompt(case)
    except Exception as e:
        print(f"PROMPT_BUILD_ERROR")
        return {
            "run_date": run_date,
            "case_id": case_id,
            "module": module,
            "scenario_label": scenario_label,
            "model": MODEL,
            "temperature": TEMPERATURE,
            "prompt_version": PROMPT_VERSION,
            "status": "prompt_build_error",
            "error": str(e),
            "raw_output": None,
            "parsed_output": None,
            "parse_error": None,
        }

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = response.content[0].text
        print(f"OK ({len(raw_text)} chars)", flush=True)
    except Exception as e:
        err_str = str(e)
        print(f"API_ERROR: {err_str[:200]}")
        return {
            "run_date": run_date,
            "case_id": case_id,
            "module": module,
            "scenario_label": scenario_label,
            "model": MODEL,
            "temperature": TEMPERATURE,
            "prompt_version": PROMPT_VERSION,
            "status": "api_error",
            "error": err_str,
            "raw_output": None,
            "parsed_output": None,
            "parse_error": None,
        }

    parsed = None
    parse_error = None
    try:
        parsed = extract_json(raw_text)
    except Exception as e:
        parse_error = str(e)

    return {
        "run_date": run_date,
        "case_id": case_id,
        "module": module,
        "scenario_label": scenario_label,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "prompt_version": PROMPT_VERSION,
        "status": "ok" if parsed is not None else "parse_error",
        "error": None,
        "raw_output": raw_text,
        "parsed_output": parsed,
        "parse_error": parse_error,
    }


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    with open(CASES_FILE) as f:
        cases_data = json.load(f)

    cases = cases_data["cases"]
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, f"run_{run_date}.jsonl")

    print(f"=== LLM Eval Run — {run_date} ===")
    print(f"Model: {MODEL}, Temp: {TEMPERATURE}")
    print(f"Cases: {len(cases)}")
    print(f"Output: {out_path}")
    print()

    results = []
    by_module = {}

    for case in cases:
        module = case["module"]
        if module not in by_module:
            print(f"\n--- {module} ---")
            by_module[module] = True
        result = run_case(client, case, run_date)
        results.append(result)
        # Small delay to avoid rate limits
        time.sleep(1)

    # Write JSONL
    with open(out_path, "w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = sum(1 for r in results if r["status"] == "ok")
    parse_err = sum(1 for r in results if r["status"] == "parse_error")
    api_err = sum(1 for r in results if r["status"] == "api_error")
    other = sum(1 for r in results if r["status"] not in ("ok", "parse_error", "api_error"))

    print(f"\n=== Summary ===")
    print(f"OK: {ok}/{len(results)}")
    print(f"Parse errors: {parse_err}")
    print(f"API errors: {api_err}")
    print(f"Other errors: {other}")
    print(f"Written: {out_path}")

    if api_err > 0:
        # Print first API error in full for diagnosis
        for r in results:
            if r["status"] == "api_error":
                print(f"\nFirst API error detail:\n{r['error']}")
                break

    # Exit 2 only if ALL cases failed — partial results are still valuable
    if ok == 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
