"""Tests for options market helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from clawdfolio.market import data as market_data


class _FakeYF:
    def __init__(self, ticker_obj):
        self._ticker_obj = ticker_obj

    def Ticker(self, _sym):
        return self._ticker_obj


class _FakeTicker:
    def __init__(self, chain_obj, expiries=None):
        self._chain_obj = chain_obj
        self.options = expiries or []

    def option_chain(self, _expiry):
        return self._chain_obj


def test_get_option_quote_prefers_moomoo(monkeypatch):
    market_data.clear_cache()

    expected = market_data.OptionQuoteData(
        ticker="TQQQ",
        expiry="2026-06-18",
        strike=60.0,
        option_type="C",
        bid=1.20,
        ask=1.30,
        last=1.25,
        source="moomoo",
    )
    monkeypatch.setattr(market_data, "_get_option_quote_moomoo", lambda *_args, **_kwargs: expected)
    monkeypatch.setattr(
        market_data, "_import_yf", lambda: (_ for _ in ()).throw(RuntimeError("no yfinance"))
    )

    quote = market_data.get_option_quote("TQQQ", "2026-06-18", 60.0, "C")

    assert quote is not None
    assert quote.source == "moomoo"
    assert quote.last == 1.25


def test_get_option_quote_fallback_yfinance(monkeypatch):
    market_data.clear_cache()

    calls = pd.DataFrame(
        [
            {
                "strike": 60.0,
                "bid": 1.10,
                "ask": 1.20,
                "lastPrice": 1.15,
                "impliedVolatility": 0.42,
                "openInterest": 321,
                "volume": 45,
            }
        ]
    )
    chain_obj = SimpleNamespace(calls=calls, puts=pd.DataFrame())
    fake_ticker = _FakeTicker(chain_obj=chain_obj)

    monkeypatch.setattr(market_data, "_get_option_quote_moomoo", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(market_data, "_import_yf", lambda: _FakeYF(fake_ticker))

    quote = market_data.get_option_quote("TQQQ", "2026-06-18", 60.0, "C")

    assert quote is not None
    assert quote.source == "yfinance"
    assert quote.bid == 1.10
    assert quote.ask == 1.20
    assert quote.last == 1.15
    assert quote.open_interest == 321
    assert quote.ref_price == 1.15


def test_get_option_chain_fallback_yfinance(monkeypatch):
    market_data.clear_cache()

    calls = pd.DataFrame(
        [
            {"contractSymbol": "TQQQ260618C00060000", "strike": 60.0, "bid": 1.10},
            {"contractSymbol": "TQQQ260618C00065000", "strike": 65.0, "bid": 0.80},
        ]
    )
    puts = pd.DataFrame(
        [
            {"contractSymbol": "TQQQ260618P00060000", "strike": 60.0, "bid": 2.10},
        ]
    )
    fake_ticker = _FakeTicker(
        chain_obj=SimpleNamespace(calls=calls, puts=puts),
        expiries=["2026-06-18", "2026-07-17"],
    )

    monkeypatch.setattr(market_data, "_get_option_chain_moomoo", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(market_data, "_import_yf", lambda: _FakeYF(fake_ticker))

    chain = market_data.get_option_chain("TQQQ", "2026-06-18")
    expiries = market_data.get_option_expiries("TQQQ")

    assert chain is not None
    assert list(chain.calls["strike"]) == [60.0, 65.0]
    assert list(chain.puts["strike"]) == [60.0]
    assert expiries == ["2026-06-18", "2026-07-17"]
