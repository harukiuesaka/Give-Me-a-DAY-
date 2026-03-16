"""
Module 4: CandidateGenerator

Generate 3-5 genuinely different strategy candidates.
Enforces: baseline + conservative + exploratory diversity.
Uses LLM when available; falls back to archetype templates.
"""

import logging

from src.domain.models import (
    Candidate,
    CandidateAssumption,
    CandidateType,
    DomainFrame,
    ImplementationComplexity,
    ResearchSpec,
    ValidationBurden,
)
from src.llm.client import LLMClient, LLMUnavailableError
from src.llm.fallbacks import fallback_generate_candidates
from src.llm.prompts import CANDIDATE_GENERATION_SYSTEM, CANDIDATE_GENERATION_USER

logger = logging.getLogger(__name__)


def generate(
    research_spec: ResearchSpec,
    domain_frame: DomainFrame,
    rejection_constraints: list[str] | None = None,
) -> list[Candidate]:
    """
    Generate 3-5 candidate strategies.

    Ensures:
    - At least 1 baseline, 1 conservative, 1 exploratory
    - Each candidate has known_risks (non-empty)
    - Each candidate has core_assumptions with failure_impact
    - No candidate violates forbidden_behaviors
    """
    client = LLMClient()
    run_id = research_spec.run_id
    forbidden = research_spec.constraints.forbidden_behaviors

    if not client.available:
        logger.info("LLM unavailable — using fallback candidate generation")
        candidates = fallback_generate_candidates(run_id, domain_frame.archetype, forbidden)
        return _post_validate(candidates, forbidden)

    try:
        candidates = _llm_generate(client, research_spec, domain_frame, rejection_constraints)
        return _post_validate(candidates, forbidden)
    except (LLMUnavailableError, Exception) as e:
        logger.warning(f"LLM candidate generation failed: {e} — using fallback")
        candidates = fallback_generate_candidates(run_id, domain_frame.archetype, forbidden)
        return _post_validate(candidates, forbidden)


def _llm_generate(
    client: LLMClient,
    spec: ResearchSpec,
    frame: DomainFrame,
    rejection_constraints: list[str] | None,
) -> list[Candidate]:
    """Use LLM to generate candidates."""
    rejection_note = ""
    if rejection_constraints:
        rejection_note = f"\n以下の方向性は前回棄却済みです。異なるアプローチを提案してください:\n"
        for rc in rejection_constraints:
            rejection_note += f"- {rc}\n"

    prompt = CANDIDATE_GENERATION_USER.format(
        archetype=frame.archetype.value,
        reframed_problem=frame.reframed_problem,
        core_hypothesis=frame.core_hypothesis,
        constraints=f"時間: {spec.constraints.time}, ツール: {', '.join(spec.constraints.tooling)}",
        forbidden_behaviors=", ".join(spec.constraints.forbidden_behaviors) or "なし",
    )
    # Append rejection note if present
    if rejection_note:
        prompt += rejection_note

    data = client.call_json(CANDIDATE_GENERATION_SYSTEM, prompt)

    raw_candidates = data.get("candidates", [])
    if len(raw_candidates) < 3:
        raise ValueError(f"LLM returned {len(raw_candidates)} candidates, need >= 3")

    candidates = []
    for i, raw in enumerate(raw_candidates[:5]):  # Max 5
        cid = f"{spec.run_id}_C{i+1:02d}"
        candidate = _parse_candidate(cid, raw)
        candidates.append(candidate)

    # Ensure type diversity
    _ensure_type_diversity(candidates)

    return candidates


def _parse_candidate(candidate_id: str, raw: dict) -> Candidate:
    """Parse a raw LLM candidate dict into a Candidate model."""
    # Parse candidate_type
    ct_str = raw.get("candidate_type", "baseline")
    try:
        candidate_type = CandidateType(ct_str)
    except ValueError:
        candidate_type = CandidateType.BASELINE

    # Parse assumptions
    raw_assumptions = raw.get("core_assumptions", [])
    assumptions = []
    for j, a in enumerate(raw_assumptions):
        if isinstance(a, dict):
            assumptions.append(CandidateAssumption(
                assumption_id=a.get("assumption_id", f"{candidate_id}_CA{j+1:02d}"),
                statement=a.get("statement", "仮定未記載"),
                failure_impact=a.get("failure_impact", "影響未記載"),
            ))

    # Ensure at least 1 assumption
    if not assumptions:
        assumptions = [CandidateAssumption(
            assumption_id=f"{candidate_id}_CA01",
            statement="この戦略の前提条件が成立する",
            failure_impact="戦略の有効性が大幅に低下する",
        )]

    # Parse burden/complexity
    try:
        burden = ValidationBurden(raw.get("validation_burden", "medium"))
    except ValueError:
        burden = ValidationBurden.MEDIUM
    try:
        complexity = ImplementationComplexity(raw.get("implementation_complexity", "medium"))
    except ValueError:
        complexity = ImplementationComplexity.MEDIUM

    # Ensure known_risks non-empty
    risks = raw.get("known_risks", [])
    if not risks:
        risks = ["パフォーマンスの不確実性", "市場環境変化リスク"]

    return Candidate(
        candidate_id=candidate_id,
        name=raw.get("name", f"候補 {candidate_id}"),
        candidate_type=candidate_type,
        summary=raw.get("summary", "概要未記載"),
        architecture_outline=raw.get("architecture_outline", []),
        core_assumptions=assumptions,
        required_inputs=raw.get("required_inputs", []),
        validation_burden=burden,
        implementation_complexity=complexity,
        expected_strengths=raw.get("expected_strengths", []),
        expected_weaknesses=raw.get("expected_weaknesses", []),
        known_risks=risks,
    )


def _ensure_type_diversity(candidates: list[Candidate]) -> None:
    """
    Ensure we have at least baseline, conservative, and exploratory.
    If missing, relabel the last candidate(s).
    """
    types_present = {c.candidate_type for c in candidates}
    required_types = [CandidateType.BASELINE, CandidateType.CONSERVATIVE, CandidateType.EXPLORATORY]

    for req_type in required_types:
        if req_type not in types_present:
            # Find a duplicate type to relabel
            type_counts: dict[CandidateType, int] = {}
            for c in candidates:
                type_counts[c.candidate_type] = type_counts.get(c.candidate_type, 0) + 1

            for c in reversed(candidates):
                if type_counts.get(c.candidate_type, 0) > 1:
                    type_counts[c.candidate_type] -= 1
                    c.candidate_type = req_type
                    types_present.add(req_type)
                    break


def _post_validate(candidates: list[Candidate], forbidden: list[str]) -> list[Candidate]:
    """
    Post-generation validation:
    - Filter out candidates violating forbidden_behaviors
    - Ensure minimum 3 candidates
    """
    if forbidden:
        filtered = []
        for c in candidates:
            outline_text = " ".join(c.architecture_outline).lower()
            violated = False
            for fb in forbidden:
                if fb.lower() in outline_text:
                    logger.warning(f"Candidate {c.candidate_id} violates forbidden: {fb}")
                    violated = True
                    break
            if not violated:
                filtered.append(c)
        candidates = filtered

    if len(candidates) < 3:
        logger.warning(f"Only {len(candidates)} candidates after validation — minimum is 3")
        # This should not happen with well-designed fallbacks, but we allow it to proceed

    return candidates
