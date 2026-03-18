"""Tests for DataAcquisition module (Round 3)."""

import numpy as np
import pandas as pd

from src.domain.models import AcquisitionStatus, QualityCheckType
from src.execution.data_acquisition import (
    _generate_synthetic_ohlcv,
    check_data_quality,
    fetch_daily_ohlcv,
    get_universe,
)


class TestGetUniverse:
    def test_factor_universe(self):
        tickers = get_universe("FACTOR")
        assert len(tickers) >= 5

    def test_unknown_archetype_defaults(self):
        tickers = get_universe("UNKNOWN_TYPE")
        assert len(tickers) >= 5

    def test_all_archetypes_have_tickers(self):
        for arch in ["FACTOR", "STAT_ARB", "EVENT", "MACRO"]:
            assert len(get_universe(arch)) >= 2


class TestSyntheticData:
    def test_generates_correct_columns(self):
        df = _generate_synthetic_ohlcv("TEST", "2020-01-01", "2023-01-01")
        for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
            assert col in df.columns

    def test_generates_business_days(self):
        df = _generate_synthetic_ohlcv("TEST", "2020-01-01", "2021-01-01")
        assert len(df) > 200

    def test_prices_are_positive(self):
        df = _generate_synthetic_ohlcv("TEST", "2020-01-01", "2023-01-01")
        assert (df["Close"] > 0).all()

    def test_marked_as_synthetic(self):
        df = _generate_synthetic_ohlcv("TEST", "2020-01-01", "2023-01-01")
        assert df.attrs.get("_synthetic") is True

    def test_deterministic_for_same_ticker(self):
        df1 = _generate_synthetic_ohlcv("SAME", "2020-01-01", "2021-01-01")
        df2 = _generate_synthetic_ohlcv("SAME", "2020-01-01", "2021-01-01")
        assert np.allclose(df1["Close"].values, df2["Close"].values)


class TestFetchDailyOhlcv:
    def test_returns_data_for_all_tickers(self):
        # Will fall back to synthetic since yfinance may not have network
        data = fetch_daily_ohlcv(["TEST1", "TEST2"], "2020-01-01", "2023-01-01")
        assert "TEST1" in data
        assert "TEST2" in data

    def test_data_has_expected_shape(self):
        data = fetch_daily_ohlcv(["TEST"], "2020-01-01", "2023-01-01")
        df = data["TEST"]
        assert len(df) > 0
        assert "Close" in df.columns


class TestDataQualityCheck:
    def test_clean_data_passes(self):
        df = _generate_synthetic_ohlcv("TEST", "2020-01-01", "2023-01-01")
        report = check_data_quality(df, "ev_test", "yfinance")
        assert report.usable_for_validation is True
        assert report.acquisition_status in (
            AcquisitionStatus.ACQUIRED, AcquisitionStatus.PARTIALLY_ACQUIRED
        )

    def test_missing_data_flagged(self):
        df = _generate_synthetic_ohlcv("TEST", "2020-01-01", "2023-01-01")
        # Inject 25% missing values
        mask = np.random.default_rng(42).random(len(df)) < 0.25
        df.loc[mask, "Close"] = np.nan
        report = check_data_quality(df, "ev_test", "yfinance")
        completeness_issues = [
            i for i in report.quality_issues
            if i.check_type == QualityCheckType.COMPLETENESS
        ]
        assert len(completeness_issues) > 0

    def test_zero_prices_flagged(self):
        df = _generate_synthetic_ohlcv("TEST", "2020-01-01", "2023-01-01")
        df.iloc[10:15, df.columns.get_loc("Close")] = 0
        report = check_data_quality(df, "ev_test", "yfinance")
        consistency_issues = [
            i for i in report.quality_issues
            if i.check_type == QualityCheckType.CONSISTENCY
        ]
        assert len(consistency_issues) > 0

    def test_synthetic_source_labeled(self):
        df = _generate_synthetic_ohlcv("TEST", "2020-01-01", "2023-01-01")
        report = check_data_quality(df, "ev_test", "yfinance")
        assert "synthetic" in report.data_source

    def test_date_range_populated(self):
        df = _generate_synthetic_ohlcv("TEST", "2020-01-01", "2023-01-01")
        report = check_data_quality(df, "ev_test", "yfinance")
        assert report.date_range_actual is not None
