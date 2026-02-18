"""Tests for Market Bubble Index module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


def _make_price_series(n: int = 300, start: float = 100.0, seed: int = 42) -> pd.Series:
    """Generate a synthetic price series."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.01, size=n)
    prices = start * np.cumprod(1 + returns)
    index = pd.bdate_range(start="2023-01-01", periods=n)
    return pd.Series(prices, index=index)


def _make_download_df(n: int = 300, start: float = 100.0, seed: int = 42) -> pd.DataFrame:
    """Make a DataFrame matching yfinance download output."""
    prices = _make_price_series(n=n, start=start, seed=seed)
    return pd.DataFrame({"Close": prices})


class TestPercentileRank:
    def test_basic_ranking(self) -> None:
        from clawdfolio.analysis.bubble import _percentile_rank

        history = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        assert _percentile_rank(3.0, history) == pytest.approx(40.0)
        assert _percentile_rank(6.0, history) == pytest.approx(100.0)
        assert _percentile_rank(0.0, history) == pytest.approx(0.0)

    def test_empty_history(self) -> None:
        from clawdfolio.analysis.bubble import _percentile_rank

        assert _percentile_rank(5.0, pd.Series(dtype=float)) == 50.0


class TestClassifyRegime:
    def test_normal(self) -> None:
        from clawdfolio.analysis.bubble import _classify_regime

        assert _classify_regime(30.0) == "NORMAL"

    def test_elevated(self) -> None:
        from clawdfolio.analysis.bubble import _classify_regime

        assert _classify_regime(70.0) == "ELEVATED"

    def test_danger(self) -> None:
        from clawdfolio.analysis.bubble import _classify_regime

        assert _classify_regime(90.0) == "DANGER"

    def test_boundary(self) -> None:
        from clawdfolio.analysis.bubble import _classify_regime

        assert _classify_regime(85.0) == "DANGER"
        assert _classify_regime(60.0) == "ELEVATED"
        assert _classify_regime(59.9) == "NORMAL"


class TestCalcQQQDeviation:
    @patch("clawdfolio.analysis.bubble._safe_download")
    def test_returns_result(self, mock_dl: MagicMock) -> None:
        from clawdfolio.analysis.bubble import calc_qqq_deviation

        mock_dl.return_value = _make_download_df(n=400)
        result = calc_qqq_deviation(lookback_years=5)
        assert result is not None
        assert result.name == "QQQ 200D Deviation"
        assert 0.0 <= result.normalized_score <= 100.0

    @patch("clawdfolio.analysis.bubble._safe_download")
    def test_insufficient_data(self, mock_dl: MagicMock) -> None:
        from clawdfolio.analysis.bubble import calc_qqq_deviation

        mock_dl.return_value = _make_download_df(n=50)
        result = calc_qqq_deviation()
        assert result is None


class TestCalcVixLevel:
    @patch("clawdfolio.analysis.bubble._safe_download")
    def test_returns_result(self, mock_dl: MagicMock) -> None:
        from clawdfolio.analysis.bubble import calc_vix_level

        mock_dl.return_value = _make_download_df(n=300, start=20.0)
        result = calc_vix_level()
        assert result is not None
        assert result.name == "VIX Level"
        assert 0.0 <= result.normalized_score <= 100.0

    @patch("clawdfolio.analysis.bubble._safe_download")
    def test_empty_data(self, mock_dl: MagicMock) -> None:
        from clawdfolio.analysis.bubble import calc_vix_level

        mock_dl.return_value = pd.DataFrame()
        result = calc_vix_level()
        assert result is None


class TestCalcSectorBreadth:
    @patch("clawdfolio.analysis.bubble._safe_download")
    def test_returns_result(self, mock_dl: MagicMock) -> None:
        from clawdfolio.analysis.bubble import calc_sector_breadth

        # All ETFs above SMA200 (uptrending)
        mock_dl.return_value = _make_download_df(n=400, start=50.0)
        result = calc_sector_breadth()
        assert result is not None
        assert result.name == "Sector Breadth"
        assert 0.0 <= result.normalized_score <= 100.0

    @patch("clawdfolio.analysis.bubble._safe_download")
    def test_no_data(self, mock_dl: MagicMock) -> None:
        from clawdfolio.analysis.bubble import calc_sector_breadth

        mock_dl.return_value = pd.DataFrame()
        result = calc_sector_breadth()
        assert result is None


class TestCalcCreditSpread:
    @patch("clawdfolio.analysis.bubble._safe_download")
    def test_returns_result(self, mock_dl: MagicMock) -> None:
        from clawdfolio.analysis.bubble import calc_credit_spread

        mock_dl.return_value = _make_download_df(n=300)
        result = calc_credit_spread()
        assert result is not None
        assert result.name == "Credit Spread (HYG/IEF)"
        assert 0.0 <= result.normalized_score <= 100.0

    @patch("clawdfolio.analysis.bubble._safe_download")
    def test_insufficient_data(self, mock_dl: MagicMock) -> None:
        from clawdfolio.analysis.bubble import calc_credit_spread

        mock_dl.return_value = _make_download_df(n=30)
        result = calc_credit_spread()
        assert result is None


class TestCalcPutCallRatio:
    @patch.dict("os.environ", {"FRED_API_KEY": "test_key"})
    def test_returns_result(self) -> None:
        from clawdfolio.analysis.bubble import calc_put_call_ratio

        mock_fred = MagicMock()
        index = pd.bdate_range(start="2023-01-01", periods=300)
        mock_fred.get_series.return_value = pd.Series(
            np.random.default_rng(42).uniform(0.5, 1.2, 300), index=index
        )
        mock_fred_cls = MagicMock(return_value=mock_fred)
        mock_fredapi = MagicMock()
        mock_fredapi.Fred = mock_fred_cls

        with patch.dict("sys.modules", {"fredapi": mock_fredapi}):
            result = calc_put_call_ratio()
        assert result is not None
        assert result.name == "Put/Call Ratio (PCCE)"
        assert 0.0 <= result.normalized_score <= 100.0

    @patch.dict("os.environ", {}, clear=True)
    def test_no_api_key(self) -> None:
        from clawdfolio.analysis.bubble import calc_put_call_ratio

        mock_fredapi = MagicMock()
        with patch.dict("sys.modules", {"fredapi": mock_fredapi}):
            result = calc_put_call_ratio()
        assert result is None


class TestCalcYieldCurve:
    @patch.dict("os.environ", {"FRED_API_KEY": "test_key"})
    def test_returns_result(self) -> None:
        from clawdfolio.analysis.bubble import calc_yield_curve

        mock_fred = MagicMock()
        index = pd.bdate_range(start="2023-01-01", periods=300)
        mock_fred.get_series.return_value = pd.Series(
            np.random.default_rng(99).uniform(-0.5, 2.0, 300), index=index
        )
        mock_fred_cls = MagicMock(return_value=mock_fred)
        mock_fredapi = MagicMock()
        mock_fredapi.Fred = mock_fred_cls

        with patch.dict("sys.modules", {"fredapi": mock_fredapi}):
            result = calc_yield_curve()
        assert result is not None
        assert result.name == "Yield Curve (10Y-2Y)"
        assert 0.0 <= result.normalized_score <= 100.0


class TestCalculateBubbleIndex:
    @patch("clawdfolio.analysis.bubble.calc_yield_curve", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_credit_spread")
    @patch("clawdfolio.analysis.bubble.calc_sector_breadth")
    @patch("clawdfolio.analysis.bubble.calc_vix_level")
    @patch("clawdfolio.analysis.bubble.calc_put_call_ratio", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_qqq_deviation")
    def test_composite_calculation(
        self,
        mock_qqq: MagicMock,
        mock_pc: MagicMock,
        mock_vix: MagicMock,
        mock_breadth: MagicMock,
        mock_credit: MagicMock,
        mock_yield: MagicMock,
    ) -> None:
        from clawdfolio.analysis.bubble import IndicatorResult, calculate_bubble_index

        mock_qqq.return_value = IndicatorResult(
            name="QQQ 200D Deviation",
            raw_value=0.1,
            normalized_score=70.0,
            percentile=70.0,
            lookback_years=5,
        )
        mock_vix.return_value = IndicatorResult(
            name="VIX Level",
            raw_value=15.0,
            normalized_score=80.0,
            percentile=20.0,
            lookback_years=5,
        )
        mock_breadth.return_value = IndicatorResult(
            name="Sector Breadth",
            raw_value=0.8,
            normalized_score=80.0,
            percentile=80.0,
            lookback_years=1,
        )
        mock_credit.return_value = IndicatorResult(
            name="Credit Spread (HYG/IEF)",
            raw_value=0.5,
            normalized_score=60.0,
            percentile=60.0,
            lookback_years=2,
        )

        result = calculate_bubble_index()

        assert 0 <= result.composite_score <= 100
        assert 0 <= result.sentiment_score <= 100
        assert 0 <= result.liquidity_score <= 100
        assert result.regime in ("NORMAL", "ELEVATED", "DANGER")
        assert result.timestamp
        assert "qqq_deviation" in result.indicators
        assert "vix_level" in result.indicators
        assert "credit_spread" in result.indicators

    @patch("clawdfolio.analysis.bubble.calc_yield_curve", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_credit_spread", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_sector_breadth", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_vix_level", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_put_call_ratio", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_qqq_deviation", return_value=None)
    def test_all_indicators_missing(self, *mocks: MagicMock) -> None:
        from clawdfolio.analysis.bubble import calculate_bubble_index

        result = calculate_bubble_index()
        # Falls back to neutral 50
        assert result.composite_score == 50.0
        assert result.regime == "NORMAL"
        assert len(result.indicators) == 0

    @patch("clawdfolio.analysis.bubble.calc_yield_curve", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_credit_spread", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_sector_breadth", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_vix_level", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_put_call_ratio", return_value=None)
    @patch("clawdfolio.analysis.bubble.calc_qqq_deviation")
    def test_danger_regime(self, mock_qqq: MagicMock, *mocks: MagicMock) -> None:
        from clawdfolio.analysis.bubble import IndicatorResult, calculate_bubble_index

        mock_qqq.return_value = IndicatorResult(
            name="QQQ", raw_value=0.3, normalized_score=95.0, percentile=95.0, lookback_years=5
        )
        result = calculate_bubble_index()
        # Only QQQ available in sentiment (weight 0.30), rest missing
        # sentiment = 95.0 (reweighted since only QQQ available: 95*0.30/0.30 = 95)
        # liquidity = 50.0 (fallback)
        # composite = 0.6*95 + 0.4*50 = 57+20 = 77
        assert result.composite_score > 70


class TestBubbleCLI:
    def test_bubble_command_console(self, capsys: pytest.CaptureFixture[str]) -> None:
        from clawdfolio.cli.main import main

        with (
            patch("clawdfolio.analysis.bubble.calc_yield_curve", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_credit_spread", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_sector_breadth", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_vix_level", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_put_call_ratio", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_qqq_deviation", return_value=None),
        ):
            rc = main(["bubble"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Market Bubble Index" in captured.out
        assert "Composite Score" in captured.out

    def test_bubble_command_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        import json

        from clawdfolio.cli.main import main

        with (
            patch("clawdfolio.analysis.bubble.calc_yield_curve", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_credit_spread", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_sector_breadth", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_vix_level", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_put_call_ratio", return_value=None),
            patch("clawdfolio.analysis.bubble.calc_qqq_deviation", return_value=None),
        ):
            rc = main(["bubble", "--export-json"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "composite_score" in data
        assert "regime" in data
