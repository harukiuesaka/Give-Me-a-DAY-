"""
Data acquisition for v1 execution layer.

v1 scope: Daily OHLCV via yfinance only.
Quality checks: completeness, consistency, temporal coverage.
Synthetic fallback when network unavailable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.domain.models import (
    AcquisitionStatus,
    DataQualityReport,
    DateRange,
    QualityCheckType,
    QualityIssue,
    QualityIssueSeverity,
)

# v1 proxy universe per archetype
PROXY_UNIVERSE: dict[str, list[str]] = {
    "FACTOR": ["1306.T", "1321.T", "2914.T", "7203.T", "6758.T",
               "9984.T", "6861.T", "4063.T", "8035.T", "6501.T"],
    "STAT_ARB": ["1306.T", "1321.T", "2914.T", "7203.T", "6758.T"],
    "EVENT": ["1306.T", "1321.T", "2914.T", "7203.T"],
    "MACRO": ["1306.T", "1321.T", "^N225"],
}


def get_universe(archetype: str) -> list[str]:
    """Return proxy ticker universe for given archetype."""
    return PROXY_UNIVERSE.get(archetype, PROXY_UNIVERSE["FACTOR"])


def fetch_daily_ohlcv(
    tickers: list[str],
    start: str,
    end: str,
) -> dict[str, pd.DataFrame]:
    """
    Fetch daily OHLCV data via yfinance.

    Returns dict mapping ticker -> DataFrame with columns:
    [Open, High, Low, Close, Volume, Adj Close]

    Falls back to synthetic data if yfinance unavailable.
    """
    results: dict[str, pd.DataFrame] = {}

    try:
        import yfinance as yf

        for ticker in tickers:
            try:
                data = yf.download(
                    ticker, start=start, end=end,
                    progress=False, auto_adjust=False,
                )
                if data is not None and len(data) > 0:
                    # Flatten multi-level columns if present
                    if isinstance(data.columns, pd.MultiIndex):
                        data.columns = data.columns.get_level_values(0)
                    results[ticker] = data
            except Exception:
                pass  # Individual ticker failure — continue
    except ImportError:
        pass  # yfinance not available

    # Fill missing tickers with synthetic data
    for ticker in tickers:
        if ticker not in results:
            results[ticker] = _generate_synthetic_ohlcv(ticker, start, end)

    return results


def _generate_synthetic_ohlcv(
    ticker: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """
    Generate synthetic daily OHLCV data.
    Clearly marked as synthetic via the _synthetic flag.
    Uses geometric Brownian motion with realistic parameters.
    """
    rng = np.random.default_rng(hash(ticker) % (2**31))
    dates = pd.bdate_range(start=start, end=end)

    if len(dates) == 0:
        dates = pd.bdate_range(start="2019-01-01", end="2024-01-01")

    n = len(dates)
    # GBM parameters: ~8% annual return, ~20% annual volatility
    dt = 1 / 252
    mu = 0.08
    sigma = 0.20
    daily_returns = rng.normal(mu * dt, sigma * np.sqrt(dt), n)

    price = 1000.0  # starting price
    closes = np.zeros(n)
    for i in range(n):
        price *= (1 + daily_returns[i])
        closes[i] = price

    highs = closes * (1 + rng.uniform(0, 0.02, n))
    lows = closes * (1 - rng.uniform(0, 0.02, n))
    opens = closes * (1 + rng.normal(0, 0.005, n))
    volumes = rng.integers(100_000, 10_000_000, n)

    df = pd.DataFrame({
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Adj Close": closes,
        "Volume": volumes,
    }, index=dates)
    df.attrs["_synthetic"] = True
    return df


def check_data_quality(
    df: pd.DataFrame,
    item_id: str,
    source: str,
) -> DataQualityReport:
    """
    Run v1 quality checks on acquired data.

    Checks: completeness, consistency, temporal.
    Returns DataQualityReport with issues flagged.
    """
    issues: list[QualityIssue] = []

    # 1. Completeness check
    total_cells = df.shape[0] * df.shape[1]
    missing_cells = int(df.isna().sum().sum())
    missing_pct = (missing_cells / total_cells * 100) if total_cells > 0 else 0.0

    if missing_pct > 0:
        severity = QualityIssueSeverity.INFO
        if missing_pct > 5:
            severity = QualityIssueSeverity.WARNING
        if missing_pct > 20:
            severity = QualityIssueSeverity.CRITICAL
        issues.append(QualityIssue(
            check_type=QualityCheckType.COMPLETENESS,
            severity=severity,
            description=f"欠損値: {missing_pct:.1f}% ({missing_cells}セル)",
            affected_rows=int(df.isna().any(axis=1).sum()),
            affected_percentage=round(missing_pct, 2),
        ))

    # 2. Consistency check (price anomalies)
    if "Close" in df.columns:
        close = df["Close"].dropna()
        if len(close) > 1:
            daily_ret = close.pct_change().dropna()
            anomalies = (daily_ret.abs() > 0.5).sum()
            if anomalies > 0:
                issues.append(QualityIssue(
                    check_type=QualityCheckType.CONSISTENCY,
                    severity=QualityIssueSeverity.WARNING,
                    description=f"日次リターン±50%超のデータポイント: {anomalies}件",
                    affected_rows=int(anomalies),
                    affected_percentage=round(anomalies / len(daily_ret) * 100, 2),
                ))

            zeros = (close <= 0).sum()
            if zeros > 0:
                issues.append(QualityIssue(
                    check_type=QualityCheckType.CONSISTENCY,
                    severity=QualityIssueSeverity.CRITICAL,
                    description=f"ゼロまたは負の株価: {zeros}件",
                    affected_rows=int(zeros),
                    affected_percentage=round(zeros / len(close) * 100, 2),
                ))

    # 3. Temporal check
    if len(df.index) > 0:
        actual_start = df.index.min()
        actual_end = df.index.max()
        expected_bdays = len(pd.bdate_range(actual_start, actual_end))
        actual_days = len(df)
        if expected_bdays > 0:
            coverage = actual_days / expected_bdays * 100
            if coverage < 90:
                issues.append(QualityIssue(
                    check_type=QualityCheckType.TEMPORAL,
                    severity=QualityIssueSeverity.WARNING,
                    description=f"時系列カバレッジ: {coverage:.0f}% (期待: {expected_bdays}日, 実際: {actual_days}日)",
                    affected_rows=expected_bdays - actual_days,
                    affected_percentage=round(100 - coverage, 2),
                ))

    # Determine overall status
    has_critical = any(i.severity == QualityIssueSeverity.CRITICAL for i in issues)
    status = AcquisitionStatus.FAILED if has_critical else AcquisitionStatus.ACQUIRED
    if issues and not has_critical:
        status = AcquisitionStatus.PARTIALLY_ACQUIRED

    date_range = None
    if len(df.index) > 0:
        date_range = DateRange(
            start=df.index.min().strftime("%Y-%m-%d"),
            end=df.index.max().strftime("%Y-%m-%d"),
        )

    is_synthetic = getattr(df, "attrs", {}).get("_synthetic", False)

    return DataQualityReport(
        evidence_item_id=item_id,
        acquisition_status=status,
        acquisition_timestamp=datetime.utcnow(),
        data_source=f"{source} (synthetic)" if is_synthetic else source,
        row_count=len(df),
        date_range_actual=date_range,
        quality_issues=issues,
        pit_status_verified="not_applicable",
        usable_for_validation=not has_critical,
    )
