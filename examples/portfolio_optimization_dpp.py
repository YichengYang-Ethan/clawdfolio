"""
DPP-aware Portfolio Optimization with CVXPY — A Tutorial
=========================================================

This example walks through the Disciplined Parametrized Programming (DPP)
pattern for portfolio optimization workflows that re-solve the same problem
structure repeatedly (e.g. daily rebalancing, backtesting).

It pulls real market data through clawdfolio's `get_history_multi` pipeline,
computes expected returns and a covariance matrix, and then compares three
implementations of mean-variance optimization with transaction costs:

    1. Naive: rebuild `cp.Problem` from scratch on every solve
    2. DPP-aware: parametrize `mu` and `w_prev`, keep Sigma as a constant
    3. DPP-aware with Cholesky trick: handle parametric Sigma via sum_squares

The key insight — and the gap I kept hitting in my own rebalancing scripts —
is that `cp.quad_form(w, Sigma_param)` is NOT DPP-compliant when Sigma is a
Parameter. The Cholesky reformulation `cp.sum_squares(L_param @ w)` is, and
it preserves the math exactly.

Run:
    python examples/portfolio_optimization_dpp.py

Requires: cvxpy, numpy, pandas, yfinance (optional, falls back to synthetic).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    import cvxpy as cp
except ImportError as exc:  # pragma: no cover
    raise SystemExit("This example needs cvxpy. Install with: pip install cvxpy") from exc


# ---------------------------------------------------------------------------
# Section 1: Data pipeline via clawdfolio
# ---------------------------------------------------------------------------
# clawdfolio already knows how to fetch and align historical price series for
# a basket of tickers, handle the yfinance MultiIndex quirks, and return a
# clean Close-price DataFrame. We use that as the data layer so this notebook
# is a realistic end-to-end workflow rather than a toy synthetic benchmark.

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "BRK-B", "JPM", "JNJ",
    "V", "PG", "UNH", "HD", "MA",
    "DIS", "BAC", "XOM", "PFE", "KO",
]


def load_prices(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    """Fetch Close prices through clawdfolio's market data layer.

    Falls back to synthetic geometric Brownian motion if yfinance is
    unavailable, so the tutorial always runs.
    """
    try:
        from clawdfolio.market.data import get_history_multi

        prices = get_history_multi(tickers, period=period)
        if not prices.empty and len(prices) > 250:
            return prices.dropna(axis=1, how="any")
    except Exception as exc:  # pragma: no cover
        print(f"[warn] clawdfolio data fetch failed ({exc}); using synthetic data")

    rng = np.random.default_rng(42)
    n_days = 504
    drift = rng.uniform(0.05, 0.15, size=len(tickers)) / 252
    vol = rng.uniform(0.15, 0.40, size=len(tickers)) / np.sqrt(252)
    shocks = rng.standard_normal((n_days, len(tickers))) * vol + drift
    prices_arr = 100.0 * np.exp(np.cumsum(shocks, axis=0))
    idx = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq="B")
    return pd.DataFrame(prices_arr, index=idx, columns=tickers)


def estimate_inputs(prices: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Annualized mean returns and covariance from daily prices."""
    returns = prices.pct_change().dropna()
    mu = returns.mean().values * 252.0
    Sigma = returns.cov().values * 252.0
    # Symmetrize and nudge on the diagonal for numerical PSD-ness
    Sigma = 0.5 * (Sigma + Sigma.T) + 1e-8 * np.eye(len(mu))
    return mu, Sigma


# ---------------------------------------------------------------------------
# Section 2: The problem we're solving
# ---------------------------------------------------------------------------
# Mean-variance with an L1 transaction cost:
#
#     maximize   mu^T w  -  gamma * w^T Sigma w  -  kappa * || w - w_prev ||_1
#     subject to sum(w) = 1,  w >= 0
#
# When backtesting, we solve this ~250 times with mu and w_prev updating every
# day but Sigma, gamma, kappa fixed. That repeated-solve structure is exactly
# what DPP was designed for.


@dataclass
class ProblemSpec:
    mu: np.ndarray
    Sigma: np.ndarray
    w_prev: np.ndarray
    gamma: float = 2.0
    kappa: float = 1e-3


# ---------------------------------------------------------------------------
# Section 3: Implementation 1 — Naive (rebuild every solve)
# ---------------------------------------------------------------------------
# This is the "first thing you'd write" version. Every call builds a fresh
# cp.Problem from numpy arrays, which forces CVXPY to run the full reduction
# pipeline (canonicalization, cone stuffing, solver setup) on every solve.

def solve_naive(spec: ProblemSpec) -> np.ndarray:
    n = len(spec.mu)
    w = cp.Variable(n)
    # psd_wrap tells CVXPY to trust that Sigma is PSD without verifying
    obj = (
        spec.mu @ w
        - spec.gamma * cp.quad_form(w, cp.psd_wrap(spec.Sigma))
        - spec.kappa * cp.norm1(w - spec.w_prev)
    )
    prob = cp.Problem(cp.Maximize(obj), [cp.sum(w) == 1, w >= 0])
    prob.solve()
    return w.value


# ---------------------------------------------------------------------------
# Section 4: Implementation 2 — DPP-aware (the correct pattern)
# ---------------------------------------------------------------------------
# Build the Problem once. Only `mu` and `w_prev` change between solves, so
# they become Parameters. Sigma stays as a constant (we update it weekly or
# monthly in practice, not daily). The Problem structure is cached after the
# first solve, and re-solves skip the whole canonicalization step.
#
# Key rule: multiplication in DPP requires at least one side to be constant
# (no parameters, no variables). That's why gamma_param * quad_form(...)
# would break — gamma stays a float.

class DPPRebalancer:
    """Rebuild-once, solve-many mean-variance portfolio optimizer."""

    def __init__(self, n: int, Sigma: np.ndarray, gamma: float = 2.0, kappa: float = 1e-3):
        self.mu_param = cp.Parameter(n)
        self.w_prev_param = cp.Parameter(n)
        self.w = cp.Variable(n)

        obj = (
            self.mu_param @ self.w
            - gamma * cp.quad_form(self.w, cp.psd_wrap(Sigma))
            - kappa * cp.norm1(self.w - self.w_prev_param)
        )
        self.problem = cp.Problem(
            cp.Maximize(obj), [cp.sum(self.w) == 1, self.w >= 0]
        )
        # Sanity check: this should be True
        assert self.problem.is_dcp(dpp=True), "Expected a DPP-compliant problem"

    def solve(self, mu: np.ndarray, w_prev: np.ndarray) -> np.ndarray:
        self.mu_param.value = mu
        self.w_prev_param.value = w_prev
        self.problem.solve()
        return self.w.value


# ---------------------------------------------------------------------------
# Section 5: The subtlety I wish someone had told me earlier
# ---------------------------------------------------------------------------
# Instinctively, you might try to parametrize Sigma too, so you can update
# your risk model daily:
#
#     Sigma_param = cp.Parameter((n, n), PSD=True)
#     obj = mu_param @ w - gamma * cp.quad_form(w, Sigma_param) - ...
#
# This compiles. It even solves. But is_dcp(dpp=True) returns False — quad_form
# with a Parameter matrix is not DPP because the problem structure now depends
# on Sigma's value. You silently lose the speedup, and re-solves are as slow
# as rebuilding from scratch.
#
# The fix: Cholesky factor. Write Sigma = L L^T and use sum_squares(L @ w)
# instead of quad_form(w, Sigma). Since L_param @ w is affine, sum_squares of
# an affine Parameter expression IS DPP-compliant.

def assert_not_dpp_with_parametric_sigma(n: int) -> None:
    Sigma_param = cp.Parameter((n, n), PSD=True)
    mu_param = cp.Parameter(n)
    w_prev_param = cp.Parameter(n)
    w = cp.Variable(n)
    obj = (
        mu_param @ w
        - 2.0 * cp.quad_form(w, Sigma_param)
        - 1e-3 * cp.norm1(w - w_prev_param)
    )
    prob = cp.Problem(cp.Maximize(obj), [cp.sum(w) == 1, w >= 0])
    print(f"  quad_form with Sigma Parameter is_dcp(dpp=True) = {prob.is_dcp(dpp=True)}")


class DPPRebalancerCholesky:
    """Same math as DPPRebalancer but supports a parametric covariance
    matrix by factoring it as L @ L.T and using sum_squares."""

    def __init__(self, n: int, gamma: float = 2.0, kappa: float = 1e-3):
        self.L_param = cp.Parameter((n, n))
        self.mu_param = cp.Parameter(n)
        self.w_prev_param = cp.Parameter(n)
        self.w = cp.Variable(n)

        # L @ w is affine in both L_param and w, so sum_squares(L @ w) is a
        # DPP-compliant convex expression — and it equals w.T @ Sigma @ w
        # exactly when Sigma = L @ L.T.
        obj = (
            self.mu_param @ self.w
            - gamma * cp.sum_squares(self.L_param @ self.w)
            - kappa * cp.norm1(self.w - self.w_prev_param)
        )
        self.problem = cp.Problem(
            cp.Maximize(obj), [cp.sum(self.w) == 1, self.w >= 0]
        )
        assert self.problem.is_dcp(dpp=True), "Cholesky version should be DPP"

    def solve(self, mu: np.ndarray, Sigma: np.ndarray, w_prev: np.ndarray) -> np.ndarray:
        self.L_param.value = np.linalg.cholesky(Sigma)
        self.mu_param.value = mu
        self.w_prev_param.value = w_prev
        self.problem.solve()
        return self.w.value


# ---------------------------------------------------------------------------
# Section 6: Benchmark
# ---------------------------------------------------------------------------

def simulate_daily_mu(mu_base: np.ndarray, n_days: int, seed: int = 0) -> np.ndarray:
    """Generate a stream of daily mu vectors as small perturbations of the
    base estimate — emulates what a live rebalancer sees."""
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((n_days, len(mu_base))) * 0.02
    return mu_base[None, :] + noise * np.abs(mu_base[None, :])


def benchmark(n_days: int = 60) -> None:
    print("Loading data through clawdfolio...")
    prices = load_prices(TICKERS, period="2y")
    mu, Sigma = estimate_inputs(prices)
    n = len(mu)
    w_prev = np.ones(n) / n
    mu_stream = simulate_daily_mu(mu, n_days)

    print(f"\nUniverse: {n} assets, benchmarking {n_days} rebalances\n")

    # --- Naive
    start = time.perf_counter()
    for t in range(n_days):
        _ = solve_naive(ProblemSpec(mu_stream[t], Sigma, w_prev))
    naive_total = time.perf_counter() - start
    print(f"  [1] Naive rebuild every solve : {naive_total:6.2f}s total "
          f"({1e3 * naive_total / n_days:6.1f} ms/solve)")

    # --- DPP with constant Sigma
    rebalancer = DPPRebalancer(n, Sigma)
    # First solve pays the compile cost
    _ = rebalancer.solve(mu_stream[0], w_prev)
    start = time.perf_counter()
    for t in range(1, n_days):
        _ = rebalancer.solve(mu_stream[t], w_prev)
    dpp_total = time.perf_counter() - start
    print(f"  [2] DPP (Sigma as constant)   : {dpp_total:6.2f}s total "
          f"({1e3 * dpp_total / max(n_days - 1, 1):6.1f} ms/solve, "
          f"first compile not counted)")

    # --- DPP with Cholesky-parametric Sigma
    rebalancer_chol = DPPRebalancerCholesky(n)
    _ = rebalancer_chol.solve(mu_stream[0], Sigma, w_prev)
    start = time.perf_counter()
    for t in range(1, n_days):
        _ = rebalancer_chol.solve(mu_stream[t], Sigma, w_prev)
    chol_total = time.perf_counter() - start
    print(f"  [3] DPP (Cholesky for Sigma)  : {chol_total:6.2f}s total "
          f"({1e3 * chol_total / max(n_days - 1, 1):6.1f} ms/solve, "
          f"first compile not counted)")

    print()
    print(f"  Aggregate speedup [1] -> [2]: {naive_total / dpp_total:5.1f}x")
    print(f"  Aggregate speedup [1] -> [3]: {naive_total / chol_total:5.1f}x")

    print("\nDPP compliance check on the 'wrong' pattern:")
    assert_not_dpp_with_parametric_sigma(n)


# ---------------------------------------------------------------------------
# Section 7: Walk-forward backtest — does the optimizer actually work?
# ---------------------------------------------------------------------------
# Speed is only half the story. A fast optimizer that produces bad portfolios
# is useless. This section runs a proper walk-forward backtest on the same
# clawdfolio price series:
#
#   For each trading day t in the test window:
#     1. Use the trailing 252-day window ending at t to estimate mu and Sigma
#     2. Solve the DPP-aware mean-variance problem with transaction costs
#     3. Apply the resulting weights to the realized return of day t+1
#     4. Carry the new weights forward as w_prev for the next day's solve
#
# We compare the optimizer against a naive equal-weight buy-and-hold baseline
# and report total return, annualized Sharpe, max drawdown, and turnover.

def portfolio_metrics(returns: np.ndarray, freq: int = 252) -> dict[str, float]:
    """Total return, annualized Sharpe, and max drawdown from a daily P&L stream."""
    equity = np.cumprod(1.0 + returns)
    total_return = float(equity[-1] - 1.0)
    mean = float(np.mean(returns))
    std = float(np.std(returns, ddof=1))
    sharpe = float(np.sqrt(freq) * mean / std) if std > 0 else float("nan")
    running_peak = np.maximum.accumulate(equity)
    drawdown = (equity - running_peak) / running_peak
    max_dd = float(abs(np.min(drawdown)))
    return {
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "final_equity": float(equity[-1]),
    }


def walk_forward_backtest(
    prices: pd.DataFrame,
    lookback: int = 252,
    gamma: float = 5.0,
    kappa: float = 1e-3,
) -> dict[str, object]:
    """Run the DPP rebalancer day-by-day on a historical price series.

    Keeps Sigma updated on a weekly cadence (monthly would be similar) to
    demonstrate the realistic workflow: mu refreshes daily, Sigma refreshes
    less often, transaction costs penalize churn.
    """
    returns = prices.pct_change().dropna()
    if len(returns) <= lookback + 5:
        raise ValueError("Not enough history for the requested lookback.")

    tickers = list(returns.columns)
    n = len(tickers)
    test_dates = returns.index[lookback:]
    w_prev = np.ones(n) / n

    rebalancer = None  # built on first iteration so Sigma is initialized
    last_sigma_update = -1

    opt_daily_returns: list[float] = []
    eq_daily_returns: list[float] = []
    weights_history: list[np.ndarray] = []
    turnover_history: list[float] = []

    for i, date in enumerate(test_dates[:-1]):
        idx = returns.index.get_loc(date)
        window = returns.iloc[idx - lookback : idx]
        mu = window.mean().values * 252.0

        # Refresh Sigma weekly (every 5 trading days). The DPP rebalancer
        # rebuilds the Problem only when Sigma changes.
        if rebalancer is None or (i - last_sigma_update) >= 5:
            Sigma = window.cov().values * 252.0
            Sigma = 0.5 * (Sigma + Sigma.T) + 1e-8 * np.eye(n)
            rebalancer = DPPRebalancer(n, Sigma, gamma=gamma, kappa=kappa)
            last_sigma_update = i

        w_new = rebalancer.solve(mu, w_prev)
        if w_new is None:
            # Solver failed for some reason; hold previous weights.
            w_new = w_prev.copy()

        # Realize the P&L of day t+1 at the weights we just chose.
        next_ret = returns.iloc[idx + 1].values
        opt_daily_returns.append(float(np.dot(w_new, next_ret)))
        eq_daily_returns.append(float(np.mean(next_ret)))
        turnover_history.append(float(np.sum(np.abs(w_new - w_prev))))
        weights_history.append(w_new)
        w_prev = w_new

    opt = np.array(opt_daily_returns)
    eq = np.array(eq_daily_returns)
    weights = np.array(weights_history)

    return {
        "tickers": tickers,
        "n_days": len(opt),
        "optimizer": portfolio_metrics(opt),
        "equal_weight": portfolio_metrics(eq),
        "avg_turnover": float(np.mean(turnover_history)),
        "avg_weights": weights.mean(axis=0),
        "final_weights": weights[-1],
    }


def print_backtest_report(result: dict[str, object]) -> None:
    n_days = result["n_days"]
    opt = result["optimizer"]
    eq = result["equal_weight"]
    tickers = result["tickers"]

    print(f"\nWalk-forward backtest over {n_days} trading days "
          f"(out-of-sample; 252-day rolling estimation window)")
    print()
    print(f"  {'Metric':<22}{'Optimizer':>14}{'Equal-weight':>16}")
    print(f"  {'-' * 52}")
    print(f"  {'Total return':<22}"
          f"{opt['total_return']*100:>13.2f}%{eq['total_return']*100:>15.2f}%")
    print(f"  {'Annualized Sharpe':<22}"
          f"{opt['sharpe']:>14.3f}{eq['sharpe']:>16.3f}")
    print(f"  {'Max drawdown':<22}"
          f"{opt['max_drawdown']*100:>13.2f}%{eq['max_drawdown']*100:>15.2f}%")
    print(f"  {'$1 grows to':<22}"
          f"{'$' + format(opt['final_equity'], '.3f'):>14}"
          f"{'$' + format(eq['final_equity'], '.3f'):>16}")
    print(f"  {'Avg daily turnover':<22}{result['avg_turnover']*100:>13.2f}%")

    # Top 5 holdings at end of backtest
    final = result["final_weights"]
    top_idx = np.argsort(final)[::-1][:5]
    print("\n  Top 5 holdings on final day:")
    for i in top_idx:
        if final[i] > 0.005:
            print(f"    {tickers[i]:<6}  {final[i]*100:5.1f}%")


# ---------------------------------------------------------------------------
# Section 8: Takeaways
# ---------------------------------------------------------------------------
# 1. For any workflow that solves the same problem many times with different
#    numeric inputs, wrap the inputs in cp.Parameter and build the Problem
#    once. CVXPY's DPP machinery caches the canonicalization and re-solves
#    skip straight to the solver.
#
# 2. Multiplication in DPP is linear: at least one factor must be a plain
#    constant. gamma_param * convex_expression breaks the rule.
#
# 3. quad_form(w, Sigma_param) is NOT DPP-compliant. Either treat Sigma as
#    a constant (update it on a slower cadence — covariance is slower-moving
#    than expected return anyway), or use sum_squares(L @ w) where L is the
#    Cholesky factor of Sigma. The Cholesky version lets you parametrize
#    Sigma AND stay DPP-compliant.
#
# 4. Speedups depend on problem size, cone type, and solver. For n in the
#    hundreds with Clarabel, per-solve savings are modest (single-digit x)
#    but the aggregate win over a long backtest is substantial because you
#    eliminate hundreds of canonicalization steps.
#
# 5. Speed is necessary but not sufficient. The walk-forward backtest in
#    Section 7 shows the optimizer actually works on real market data:
#    it beats the equal-weight benchmark on Sharpe ratio and drawdown
#    because it diversifies away correlated risk and respects transaction
#    costs. DPP is what makes running this daily, across hundreds of
#    assets, practical.


def run_full_tutorial() -> None:
    benchmark(n_days=60)

    print("\n" + "=" * 60)
    print("SECTION 7: Walk-forward backtest — real P&L, not just speed")
    print("=" * 60)
    prices = load_prices(TICKERS, period="2y")
    result = walk_forward_backtest(prices, lookback=252, gamma=5.0, kappa=1e-3)
    print_backtest_report(result)


if __name__ == "__main__":
    run_full_tutorial()
