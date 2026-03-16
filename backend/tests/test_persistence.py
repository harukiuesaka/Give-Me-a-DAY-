"""Tests for PersistenceStore and AuditLogger (Round 1)."""

import tempfile
import uuid
from datetime import datetime

import pytest

from src.domain.models import (
    AuditEvent,
    RiskPreference,
    RunMeta,
    RunStatus,
    TimeHorizonPreference,
    UserIntent,
)
from src.persistence.audit_log import AuditLogger
from src.persistence.store import PersistenceStore


@pytest.fixture
def store(tmp_path):
    return PersistenceStore(data_dir=str(tmp_path / "data"))


@pytest.fixture
def audit_logger(tmp_path):
    return AuditLogger(data_dir=str(tmp_path / "data" / "audit_log"))


def test_save_and_load_run_meta(store):
    meta = RunMeta(
        run_id="run_test001",
        created_at=datetime.utcnow(),
        status=RunStatus.PENDING,
    )
    store.save_run_meta("run_test001", meta)
    loaded = store.load_run_meta("run_test001")
    assert loaded["run_id"] == "run_test001"
    assert loaded["status"] == "pending"


def test_save_and_load_run_object(store):
    intent = UserIntent(
        run_id="run_test001",
        created_at=datetime.utcnow(),
        raw_goal="日本株でモメンタム戦略を検証したい",
        user_goal_summary="日本株のモメンタム戦略を検証",
        success_definition="年率10%のリターン",
        risk_preference=RiskPreference.MEDIUM,
        time_horizon_preference=TimeHorizonPreference.ONE_WEEK,
    )
    store.save_run_object("run_test001", "user_intent", intent)
    loaded = store.load_run_object("run_test001", "user_intent")
    assert loaded["run_id"] == "run_test001"
    assert loaded["raw_goal"] == "日本株でモメンタム戦略を検証したい"


def test_run_exists(store):
    assert not store.run_exists("nonexistent")
    meta = RunMeta(
        run_id="run_exists",
        created_at=datetime.utcnow(),
        status=RunStatus.PENDING,
    )
    store.save_run_meta("run_exists", meta)
    assert store.run_exists("run_exists")


def test_audit_logger_append_and_read(audit_logger):
    event = AuditEvent(
        event_id=f"evt_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.utcnow(),
        run_id="run_test001",
        event_type="pipeline.started",
        module="orchestrator",
        details={"raw_goal": "test goal"},
    )
    audit_logger.append_event(event)

    events = audit_logger.read_events("run_test001", "pipeline_events.jsonl")
    assert len(events) == 1
    assert events[0]["event_type"] == "pipeline.started"
