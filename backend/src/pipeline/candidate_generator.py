"""
Module 5: CandidateGenerator — stub.

TODO: Round 2 — Generate 3-5 candidate strategies.
"""

from src.domain.models import Candidate, DomainFrame, ResearchSpec


def generate(
    research_spec: ResearchSpec,
    domain_frame: DomainFrame,
    rejection_constraints: list[str] | None = None,
) -> list[Candidate]:
    """Generate candidates. TODO: Round 2."""
    raise NotImplementedError("CandidateGenerator is a Round 2 implementation target.")
