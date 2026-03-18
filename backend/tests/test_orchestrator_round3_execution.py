"""Integration checks for Round 3 execution layer orchestration."""

import tempfile

import pytest

from src.api.schemas import CreateRunRequest
from src.pipeline.orchestrator import execute_pipeline


@pytest.fixture
def tmp_data_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setattr("src.config.settings.DATA_DIR", d)
        import src.api.dependencies as deps
        deps._store = None
        deps._audit_logger = None
        yield d
        deps._store = None
        deps._audit_logger = None


def test_execution_artifacts_are_persisted(tmp_data_dir):
    run_id = "run_orch_r3_001"
    request = CreateRunRequest(goal="日本株のモメンタム候補を比較検証したい", risk="medium")

    execute_pipeline(run_id, request)

    from src.api.dependencies import get_store
    store = get_store()

    meta = store.load_run_meta(run_id)
    assert meta["status"] == "completed"
    assert meta["steps_total"] == 12

    dq_reports = store.load_all_candidate_objects(run_id, "quality_reports")
    test_results = store.load_all_candidate_objects(run_id, "test_results")
    cmp_res = store.load_run_object(run_id, "comparison_result")
    cards = store.load_presentation(run_id, "candidate_cards.json")
    context = store.load_presentation(run_id, "presentation_context.json")

    assert len(dq_reports) >= 3
    assert len(test_results) >= 3
    assert "comparison_matrix" in cmp_res
    assert len(cards) <= 2
    assert "validation_summary" in context
