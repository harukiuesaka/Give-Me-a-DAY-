"""Tests for orchestrator Round 2 pipeline flow."""

import json
import tempfile

import pytest

from src.api.schemas import CreateRunRequest
from src.pipeline.orchestrator import execute_pipeline


@pytest.fixture
def tmp_data_dir(monkeypatch):
    """Provide a temp directory for persistence."""
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setattr("src.config.settings.DATA_DIR", d)
        # Reset singletons
        import src.api.dependencies as deps
        deps._store = None
        deps._audit_logger = None
        yield d
        deps._store = None
        deps._audit_logger = None


class TestOrchestratorRound2:
    def test_happy_path_completes(self, tmp_data_dir):
        """Full pipeline runs to completion with fallback (no LLM)."""
        request = CreateRunRequest(
            goal="日本株でモメンタム戦略を検証したい",
            risk="medium",
            time_horizon="one_week",
        )
        run_id = "run_orch_r2_001"

        result = execute_pipeline(run_id, request)
        assert result == run_id

        # Verify all artifacts are persisted
        from src.api.dependencies import get_store
        store = get_store()

        meta = store.load_run_meta(run_id)
        assert meta["status"] == "completed"

        # Check pipeline objects exist
        user_intent = store.load_run_object(run_id, "user_intent")
        assert user_intent["domain"] == "investment_research"

        domain_frame = store.load_run_object(run_id, "domain_frame")
        assert domain_frame["archetype"] in [
            "FACTOR", "STAT_ARB", "EVENT", "MACRO",
            "ML_SIGNAL", "ALT_DATA", "HYBRID", "UNCLASSIFIED",
        ]

        research_spec = store.load_run_object(run_id, "research_spec")
        assert research_spec["spec_id"] == f"{run_id}-RS"

        candidates = store.load_all_candidate_objects(run_id, "candidates")
        assert len(candidates) >= 3

        evidence_plans = store.load_all_candidate_objects(run_id, "evidence_plans")
        assert len(evidence_plans) >= 3

        validation_plans = store.load_all_candidate_objects(run_id, "validation_plans")
        assert len(validation_plans) >= 3

    def test_candidates_have_required_fields(self, tmp_data_dir):
        """Each candidate must have known_risks and core_assumptions."""
        request = CreateRunRequest(
            goal="日本株でバリューファクター戦略を検証したい",
            risk="low",
            time_horizon="one_month",
        )
        execute_pipeline("run_orch_r2_002", request)

        from src.api.dependencies import get_store
        store = get_store()
        candidates = store.load_all_candidate_objects("run_orch_r2_002", "candidates")

        for c in candidates:
            assert len(c.get("known_risks", [])) >= 1
            assert len(c.get("core_assumptions", [])) >= 1

    def test_validation_plans_have_failure_conditions(self, tmp_data_dir):
        """Every test in every validation plan must have failure conditions."""
        request = CreateRunRequest(
            goal="日本株でモメンタム投資戦略を検証したい",
            risk="medium",
            time_horizon="one_week",
        )
        execute_pipeline("run_orch_r2_003", request)

        from src.api.dependencies import get_store
        store = get_store()
        plans = store.load_all_candidate_objects("run_orch_r2_003", "validation_plans")

        for vp in plans:
            for test in vp.get("test_sequence", []):
                assert len(test.get("failure_conditions", [])) >= 1, \
                    f"Test {test.get('test_id')} has no failure conditions"

    def test_non_investment_goal_fails(self, tmp_data_dir):
        """Non-investment goal should fail at goal intake."""
        from src.pipeline.goal_intake import DomainOutOfScopeError
        request = CreateRunRequest(
            goal="天気予報を改善するAIを作りたいです")

        with pytest.raises(DomainOutOfScopeError):
            execute_pipeline("run_orch_r2_fail", request)
