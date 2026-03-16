"""Tests for Goal Intake module (Round 1)."""

import pytest

from src.api.schemas import CreateRunRequest
from src.domain.models import RiskPreference, TimeHorizonPreference
from src.pipeline.goal_intake import (
    DomainOutOfScopeError,
    classify_domain,
    process_goal_intake,
)


def test_classify_domain_investment():
    assert classify_domain("日本株でモメンタム戦略を試したい") == "investment_research"


def test_classify_domain_non_investment():
    with pytest.raises(DomainOutOfScopeError):
        classify_domain("天気をよくしたい")


def test_process_goal_intake_basic():
    request = CreateRunRequest(
        goal="日本株で12ヶ月モメンタム戦略を検証したい",
        risk="medium",
        time_horizon="one_week",
    )
    intent = process_goal_intake("run_test001", request)

    assert intent.run_id == "run_test001"
    assert intent.domain == "investment_research"
    assert intent.risk_preference == RiskPreference.MEDIUM
    assert intent.time_horizon_preference == TimeHorizonPreference.ONE_WEEK
    assert intent.raw_goal == "日本株で12ヶ月モメンタム戦略を検証したい"


def test_process_goal_intake_defaults():
    request = CreateRunRequest(
        goal="日本株で投資戦略を検証したい",
    )
    intent = process_goal_intake("run_test002", request)

    assert intent.risk_preference == RiskPreference.MEDIUM
    assert intent.time_horizon_preference == TimeHorizonPreference.ONE_WEEK
    assert len(intent.open_uncertainties) > 0


def test_process_goal_intake_with_exclusions():
    request = CreateRunRequest(
        goal="日本株でモメンタム戦略を検証したい",
        exclusions=["空売りの禁止", "レバレッジの使用禁止"],
    )
    intent = process_goal_intake("run_test003", request)

    assert "空売りの禁止" in intent.must_not_do
    assert "レバレッジの使用禁止" in intent.must_not_do
