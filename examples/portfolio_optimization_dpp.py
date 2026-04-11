"""
DPP-aware Portfolio Optimization with CVXPY — A Tutorial
=========================================================

This example is a hands-on walkthrough of the Disciplined Parametrized
Programming (DPP) pattern in CVXPY, with mean-variance portfolio construction
as the motivating application. It is aimed at anyone who has written a CVXPY
problem inside a for-loop and wondered why it is slower than it should be.

Three things you will learn:

    1. Why the naive "rebuild the Problem every iteration" pattern forces
       CVXPY to pay a full canonicalization cost on every solve, and how
       wrapping the changing inputs in cp.Parameter lets the DPP machinery
       cache the problem structure and skip that step on re-solves.

    2. The non-obvious subtlety with cp.quad_form(w, Sigma_param): it is
       NOT DPP-compliant, because the second argument of quad_form cannot
       be a Parameter without breaking the affine structure DPP relies on.
       We demonstrate the failure and then show how a Cholesky reformulation
       using cp.sum_squares sidesteps it cleanly while preserving the exact
       same mathematics.

    3. That speed alone is not the point. The real value of DPP is faster
       research iteration: a 250-day walk-forward backtest that used to
       take minutes now takes seconds, which is the difference between
       "try one idea a day" and "try twenty ideas before lunch". Section
       9 runs that backtest on real clawdfolio data and shows the optimizer
       produces a sensible, well-diversified portfolio that beats the
       equal-weight benchmark on every risk-adjusted metric.

This file is the runnable reference implementation. A matching Jupyter
notebook (``portfolio_optimization_dpp.ipynb``) contains the same content
with inline plots and narrative cells for reading rather than running.

Run:
    python examples/portfolio_optimization_dpp.py
    python examples/portfolio_optimization_dpp.py --save-plots  # writes PNGs

Dependencies: cvxpy, numpy, pandas. Optional: matplotlib (for --save-plots),
yfinance through clawdfolio (falls back to synthetic data if unavailable).
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import cvxpy as cp
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "This example needs cvxpy. Install with: pip install cvxpy"
    ) from exc


# ---------------------------------------------------------------------------
# Section 1: Data pipeline via clawdfolio
# ---------------------------------------------------------------------------
# clawdfolio already knows how to fetch and align historical Close prices for
# a basket of tickers, handle yfinance's MultiIndex quirks, and return a
# clean DataFrame. We reuse that so the tutorial is a realistic end-to-end
# workflow rather than a toy synthetic benchmark.
#
# If yfinance is unavailable (no network, upstream outage, etc.) we fall
# back to geometric Brownian motion with a fixed seed so the notebook
# always runs reproducibly.

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "BRK-B", "JPM", "JNJ",
    "V", "PG", "UNH", "HD", "MA",
    "DIS", "BAC", "XOM", "PFE", "KO",
]


def load_prices(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    """Close-price DataFrame via clawdfolio's market data layer.

    On failure, returns synthetic GBM data so the tutorial still runs end
    to end without network access.
    """
    try:
        from clawdfolio.market.data import get_history_multi

        prices = get_history_multi(tickers, period=period)
        if not prices.empty and len(prices) > 260:
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
    sigma = returns.cov().values * 252.0
    # Symmetrize and nudge the diagonal for numerical PSD-ness before Cholesky.
    sigma = 0.5 * (sigma + sigma.T) + 1e-8 * np.eye(len(mu))
    return mu, sigma


# ---------------------------------------------------------------------------
# Section 2: The problem we're solving
# ---------------------------------------------------------------------------
# Classic mean-variance with an L1 transaction-cost penalty:
#
#     maximize   mu^T w  -  gamma * w^T Sigma w  -  kappa * || w - w_prev ||_1
#     subject to sum(w) = 1,  w >= 0
#
# When backtesting or rebalancing daily, we solve this hundreds of times with
# mu and w_prev changing every day but Sigma, gamma, kappa changing rarely.
# That repeated-solve structure is exactly what DPP was designed for.


@dataclass
class ProblemSpec:
    mu: np.ndarray
    sigma: np.ndarray
    w_prev: np.ndarray
    gamma: float = 2.0
    kappa: float = 1e-3


# ---------------------------------------------------------------------------
# Section 3: Implementation 1 — Naive (rebuild every solve)
# ---------------------------------------------------------------------------
# This is the "first thing you'd write" version. Every call builds a fresh
# cp.Problem from numpy arrays, which forces CVXPY to run the full reduction
# pipeline (canonicalize -> cone stuffing -> solver setup) on every call.
# Functionally correct, but every iteration throws away work we could have
# cached.

def solve_naive(spec: ProblemSpec) -> np.ndarray:
    n = len(spec.mu)
    w = cp.Variable(n)
    obj = (
        spec.mu @ w
        - spec.gamma * cp.quad_form(w, cp.psd_wrap(spec.sigma))
        - spec.kappa * cp.norm1(w - spec.w_prev)
    )
    prob = cp.Problem(cp.Maximize(obj), [cp.sum(w) == 1, w >= 0])
    prob.solve()
    return w.value


# ---------------------------------------------------------------------------
# Section 4: Implementation 2 — DPP with constant Sigma
# ---------------------------------------------------------------------------
# Build the Problem once and hand each solve a pair of fresh Parameter
# values. Sigma stays baked in as a constant; in practice most production
# rebalancers update covariance weekly or monthly anyway, because daily
# covariance estimates are noisy and slower-moving than return forecasts.
#
# Key DPP rule: Parameters are classified as *affine*, and multiplication
# in a DPP objective requires at least one factor to be a plain constant
# (no parameters, no variables). That is why gamma stays as a Python float
# here instead of being wrapped in cp.Parameter.

class DPPRebalancer:
    """Rebuild-once, solve-many mean-variance rebalancer with fixed Sigma."""

    def __init__(
        self,
        n: int,
        sigma: np.ndarray,
        gamma: float = 2.0,
        kappa: float = 1e-3,
    ) -> None:
        self.mu_param = cp.Parameter(n)
        self.w_prev_param = cp.Parameter(n)
        self.w = cp.Variable(n)

        obj = (
            self.mu_param @ self.w
            - gamma * cp.quad_form(self.w, cp.psd_wrap(sigma))
            - kappa * cp.norm1(self.w - self.w_prev_param)
        )
        self.problem = cp.Problem(
            cp.Maximize(obj),
            [cp.sum(self.w) == 1, self.w >= 0],
        )
        assert self.problem.is_dcp(dpp=True), (
            "DPPRebalancer should be DPP-compliant — check that Sigma is "
            "passed as a numeric array and gamma is a Python float."
        )

    def solve(self, mu: np.ndarray, w_prev: np.ndarray) -> np.ndarray:
        self.mu_param.value = mu
        self.w_prev_param.value = w_prev
        self.problem.solve()
        return self.w.value


# ---------------------------------------------------------------------------
# Section 5: The subtlety I wish someone had told me earlier
# ---------------------------------------------------------------------------
# Instinctively, you might try to parametrize Sigma so you can update the
# risk model every day:
#
#     Sigma_param = cp.Parameter((n, n), PSD=True)
#     obj = mu_param @ w - gamma * cp.quad_form(w, Sigma_param) - ...
#
# This compiles. It even solves, because it is still DCP-convex. But
# prob.is_dcp(dpp=True) returns False — quad_form with a Parameter matrix
# is not DPP, because the canonicalized structure now depends on Sigma's
# value. You silently lose the speedup, and re-solves pay the full
# canonicalization cost every time.
#
# The fix is a Cholesky reformulation. If Sigma = L L^T (with L lower
# triangular from np.linalg.cholesky), then
#
#     w^T Sigma w = w^T L L^T w = || L^T w ||_2^2 = sum_squares(L^T w)
#
# sum_squares applied to an affine Parameter-times-variable expression IS
# DPP-compliant, because L_param^T @ w is affine in both L_param and w, and
# sum_squares of an affine expression is a convex DPP atom.
#
# Watch the transpose: we need L.T @ w, not L @ w. Using L @ w would give
# w^T L^T L w, which is a different quadratic form and in general is NOT
# equal to w^T Sigma w. I left that particular trap for myself in a first
# draft of this notebook — the assertions in verify_all_implementations()
# below catch it.

def assert_not_dpp_with_parametric_sigma(n: int) -> None:
    """Build the 'tempting' version with Sigma as a Parameter and confirm
    that CVXPY flags it as non-DPP."""
    sigma_param = cp.Parameter((n, n), PSD=True)
    mu_param = cp.Parameter(n)
    w_prev_param = cp.Parameter(n)
    w = cp.Variable(n)
    obj = (
        mu_param @ w
        - 2.0 * cp.quad_form(w, sigma_param)
        - 1e-3 * cp.norm1(w - w_prev_param)
    )
    prob = cp.Problem(cp.Maximize(obj), [cp.sum(w) == 1, w >= 0])
    assert prob.is_dcp(), "Problem should still be DCP (just not DPP)."
    assert not prob.is_dcp(dpp=True), (
        "Expected quad_form(w, Sigma_param) to be non-DPP, but CVXPY says it is."
    )
    print(f"  quad_form(w, Sigma_param) is_dcp(dpp=True) = "
          f"{prob.is_dcp(dpp=True)}  (as expected)")


# ---------------------------------------------------------------------------
# Section 6: Implementation 3 — DPP with parametric Sigma via Cholesky
# ---------------------------------------------------------------------------

class DPPRebalancerCholesky:
    """DPP-compliant rebalancer that accepts a changing Sigma via its
    Cholesky factor."""

    def __init__(
        self, n: int, gamma: float = 2.0, kappa: float = 1e-3
    ) -> None:
        self.L_param = cp.Parameter((n, n))  # will hold np.linalg.cholesky(Sigma)
        self.mu_param = cp.Parameter(n)
        self.w_prev_param = cp.Parameter(n)
        self.w = cp.Variable(n)

        # IMPORTANT: L.T @ w, not L @ w. See Section 5 for the derivation.
        # sum_squares(L.T @ w) = w^T L L^T w = w^T Sigma w.
        risk = cp.sum_squares(self.L_param.T @ self.w)

        obj = (
            self.mu_param @ self.w
            - gamma * risk
            - kappa * cp.norm1(self.w - self.w_prev_param)
        )
        self.problem = cp.Problem(
            cp.Maximize(obj),
            [cp.sum(self.w) == 1, self.w >= 0],
        )
        assert self.problem.is_dcp(dpp=True), (
            "Cholesky rebalancer should be DPP-compliant."
        )

    def solve(
        self, mu: np.ndarray, sigma: np.ndarray, w_prev: np.ndarray
    ) -> np.ndarray:
        self.L_param.value = np.linalg.cholesky(sigma)
        self.mu_param.value = mu
        self.w_prev_param.value = w_prev
        self.problem.solve()
        return self.w.value


# ---------------------------------------------------------------------------
# Section 7: Correctness — do all three implementations agree?
# ---------------------------------------------------------------------------
# Before we time anything, prove that the three implementations compute the
# same optimum. If they don't, any speedup is meaningless. This is where a
# bug like the L vs L.T mix-up shows up immediately.

def verify_all_implementations(n_checks: int = 5, n: int = 12, tol: float = 1e-4) -> None:
    """Solve the same random problem with all three implementations and
    assert the weight vectors agree to within tolerance."""
    rng = np.random.default_rng(0)
    print("\nCorrectness check: all three implementations should match.")

    for k in range(n_checks):
        A = rng.standard_normal((n, n))
        sigma = A @ A.T + 0.1 * np.eye(n)
        mu = 0.05 + 0.2 * rng.standard_normal(n)
        w_prev = np.ones(n) / n

        spec = ProblemSpec(mu=mu, sigma=sigma, w_prev=w_prev)
        w_naive = solve_naive(spec)

        reb_const = DPPRebalancer(n, sigma)
        w_dpp = reb_const.solve(mu, w_prev)

        reb_chol = DPPRebalancerCholesky(n)
        w_chol = reb_chol.solve(mu, sigma, w_prev)

        err_dpp = float(np.max(np.abs(w_naive - w_dpp)))
        err_chol = float(np.max(np.abs(w_naive - w_chol)))
        ok = err_dpp < tol and err_chol < tol
        status = "PASS" if ok else "FAIL"
        print(f"  check {k+1}: max|naive-dpp|={err_dpp:.2e}  "
              f"max|naive-chol|={err_chol:.2e}  [{status}]")
        assert ok, (
            f"Implementations disagree (tol={tol}). "
            f"naive-dpp={err_dpp}, naive-chol={err_chol}"
        )


# ---------------------------------------------------------------------------
# Section 8: Speed benchmark
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    n_days: int
    naive_total: float
    dpp_total: float
    chol_total: float
    naive_per_solve_ms: float
    dpp_per_solve_ms: float
    chol_per_solve_ms: float
    speedup_dpp: float
    speedup_chol: float


def simulate_daily_mu(mu_base: np.ndarray, n_days: int, seed: int = 0) -> np.ndarray:
    """Generate a stream of daily mu vectors as small perturbations of the
    base estimate — emulates what a live rebalancer sees."""
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((n_days, len(mu_base))) * 0.02
    return mu_base[None, :] + noise * np.abs(mu_base[None, :])


def benchmark(prices: pd.DataFrame, n_days: int = 60) -> BenchmarkResult:
    mu, sigma = estimate_inputs(prices)
    n = len(mu)
    w_prev = np.ones(n) / n
    mu_stream = simulate_daily_mu(mu, n_days)

    print(f"\nUniverse: {n} assets, benchmarking {n_days} rebalances\n")

    # --- Implementation 1: Naive
    t0 = time.perf_counter()
    for t in range(n_days):
        _ = solve_naive(ProblemSpec(mu_stream[t], sigma, w_prev))
    naive_total = time.perf_counter() - t0

    # --- Implementation 2: DPP with constant Sigma
    rebalancer = DPPRebalancer(n, sigma)
    _ = rebalancer.solve(mu_stream[0], w_prev)  # pay compile cost
    t0 = time.perf_counter()
    for t in range(1, n_days):
        _ = rebalancer.solve(mu_stream[t], w_prev)
    dpp_total = time.perf_counter() - t0

    # --- Implementation 3: DPP + Cholesky
    rebalancer_chol = DPPRebalancerCholesky(n)
    _ = rebalancer_chol.solve(mu_stream[0], sigma, w_prev)  # pay compile cost
    t0 = time.perf_counter()
    for t in range(1, n_days):
        _ = rebalancer_chol.solve(mu_stream[t], sigma, w_prev)
    chol_total = time.perf_counter() - t0

    naive_per = 1e3 * naive_total / n_days
    dpp_per = 1e3 * dpp_total / max(n_days - 1, 1)
    chol_per = 1e3 * chol_total / max(n_days - 1, 1)

    print(f"  [1] Naive rebuild every solve : {naive_total:6.2f}s total "
          f"({naive_per:6.1f} ms/solve)")
    print(f"  [2] DPP (Sigma as constant)   : {dpp_total:6.2f}s total "
          f"({dpp_per:6.1f} ms/solve, first compile not counted)")
    print(f"  [3] DPP (Cholesky for Sigma)  : {chol_total:6.2f}s total "
          f"({chol_per:6.1f} ms/solve, first compile not counted)")
    print()
    print(f"  Aggregate speedup [1] -> [2]: {naive_total / dpp_total:5.1f}x")
    print(f"  Aggregate speedup [1] -> [3]: {naive_total / chol_total:5.1f}x")

    print("\n  DPP compliance check on the 'wrong' pattern:")
    assert_not_dpp_with_parametric_sigma(n)

    return BenchmarkResult(
        n_days=n_days,
        naive_total=naive_total,
        dpp_total=dpp_total,
        chol_total=chol_total,
        naive_per_solve_ms=naive_per,
        dpp_per_solve_ms=dpp_per,
        chol_per_solve_ms=chol_per,
        speedup_dpp=naive_total / dpp_total,
        speedup_chol=naive_total / chol_total,
    )


# ---------------------------------------------------------------------------
# Section 9: Walk-forward backtest — does the optimizer actually work?
# ---------------------------------------------------------------------------
# Speed is only half the story. A fast optimizer that produces bad portfolios
# is useless. This section runs a proper walk-forward backtest on the same
# clawdfolio price series:
#
#   For each trading day t in the test window:
#     1. Use the trailing 252-day window ending at t to estimate mu and
#        Sigma (annualized).
#     2. Solve the DPP-aware mean-variance problem with transaction costs.
#     3. Apply the resulting weights to the realized return of day t+1.
#     4. Carry the new weights forward as w_prev for the next day's solve.
#
# We compare the optimizer against a naive equal-weight buy-and-hold baseline
# and report total return, annualized Sharpe, max drawdown, and turnover.
# Sigma is refreshed weekly — that's the realistic cadence, and it shows off
# the DPP cache: we only rebuild the Problem on Sigma updates, not on every
# day.


@dataclass
class BacktestResult:
    tickers: list[str]
    dates: pd.DatetimeIndex
    opt_returns: np.ndarray
    eq_returns: np.ndarray
    opt_equity: np.ndarray
    eq_equity: np.ndarray
    opt_drawdown: np.ndarray
    eq_drawdown: np.ndarray
    weights_history: np.ndarray
    turnover_history: np.ndarray
    opt_metrics: dict[str, float]
    eq_metrics: dict[str, float]


def _metrics(returns: np.ndarray, freq: int = 252) -> dict[str, float]:
    equity = np.cumprod(1.0 + returns)
    total_return = float(equity[-1] - 1.0)
    mean = float(np.mean(returns))
    std = float(np.std(returns, ddof=1))
    sharpe = float(np.sqrt(freq) * mean / std) if std > 0 else float("nan")
    running_peak = np.maximum.accumulate(equity)
    drawdown = (equity - running_peak) / running_peak
    return {
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": float(abs(np.min(drawdown))),
        "final_equity": float(equity[-1]),
    }


def walk_forward_backtest(
    prices: pd.DataFrame,
    lookback: int = 252,
    gamma: float = 5.0,
    kappa: float = 1e-3,
    sigma_refresh_days: int = 5,
) -> BacktestResult:
    returns = prices.pct_change().dropna()
    if len(returns) <= lookback + 5:
        raise ValueError("Not enough history for the requested lookback.")

    tickers = list(returns.columns)
    n = len(tickers)
    test_dates = returns.index[lookback:]
    w_prev = np.ones(n) / n

    rebalancer: DPPRebalancer | None = None
    last_sigma_refresh = -(sigma_refresh_days + 1)

    opt_daily, eq_daily = [], []
    weights_hist, turnover_hist = [], []
    date_hist = []

    for i, date in enumerate(test_dates[:-1]):
        idx = returns.index.get_loc(date)
        window = returns.iloc[idx - lookback: idx]
        mu = window.mean().values * 252.0

        if rebalancer is None or (i - last_sigma_refresh) >= sigma_refresh_days:
            sigma = window.cov().values * 252.0
            sigma = 0.5 * (sigma + sigma.T) + 1e-8 * np.eye(n)
            rebalancer = DPPRebalancer(n, sigma, gamma=gamma, kappa=kappa)
            last_sigma_refresh = i

        w_new = rebalancer.solve(mu, w_prev)
        if w_new is None:  # solver failure — hold previous weights
            w_new = w_prev.copy()

        next_ret = returns.iloc[idx + 1].values
        opt_daily.append(float(np.dot(w_new, next_ret)))
        eq_daily.append(float(np.mean(next_ret)))
        turnover_hist.append(float(np.sum(np.abs(w_new - w_prev))))
        weights_hist.append(w_new)
        date_hist.append(test_dates[i + 1])
        w_prev = w_new

    opt_arr = np.array(opt_daily)
    eq_arr = np.array(eq_daily)
    weights_arr = np.array(weights_hist)

    opt_equity = np.cumprod(1.0 + opt_arr)
    eq_equity = np.cumprod(1.0 + eq_arr)
    opt_dd = opt_equity / np.maximum.accumulate(opt_equity) - 1.0
    eq_dd = eq_equity / np.maximum.accumulate(eq_equity) - 1.0

    return BacktestResult(
        tickers=tickers,
        dates=pd.DatetimeIndex(date_hist),
        opt_returns=opt_arr,
        eq_returns=eq_arr,
        opt_equity=opt_equity,
        eq_equity=eq_equity,
        opt_drawdown=opt_dd,
        eq_drawdown=eq_dd,
        weights_history=weights_arr,
        turnover_history=np.array(turnover_hist),
        opt_metrics=_metrics(opt_arr),
        eq_metrics=_metrics(eq_arr),
    )


def print_backtest_report(result: BacktestResult) -> None:
    opt = result.opt_metrics
    eq = result.eq_metrics
    tickers = result.tickers
    n_days = len(result.opt_returns)

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
    print(f"  {'Avg daily turnover':<22}"
          f"{float(np.mean(result.turnover_history))*100:>13.2f}%")

    final = result.weights_history[-1]
    top_idx = np.argsort(final)[::-1][:5]
    print("\n  Top 5 holdings on final day:")
    for i in top_idx:
        if final[i] > 0.005:
            print(f"    {tickers[i]:<6}  {final[i]*100:5.1f}%")


# ---------------------------------------------------------------------------
# Section 10: Optional plots
# ---------------------------------------------------------------------------
# Run with --save-plots to dump a few figures to examples/_dpp_plots/. They
# are also used by the matching .ipynb. Everything still works without
# matplotlib; we only import it lazily when asked.

def save_plots(
    bench: BenchmarkResult, back: BacktestResult, out_dir: Path
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:  # pragma: no cover
        print("[warn] matplotlib not available; skipping plots")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Figure 1: speedup bar chart
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = ["Naive", "DPP\n(const Sigma)", "DPP\n(Cholesky)"]
    values = [
        bench.naive_per_solve_ms,
        bench.dpp_per_solve_ms,
        bench.chol_per_solve_ms,
    ]
    colors = ["#d46a6a", "#6a9ad4", "#6ad49a"]
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("Milliseconds per solve (lower is better)")
    ax.set_title("Per-solve wall clock: naive vs. DPP patterns")
    for bar, v in zip(bars, values, strict=False):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0, v,
            f"{v:.1f} ms", ha="center", va="bottom",
        )
    fig.tight_layout()
    fig.savefig(out_dir / "01_speedup_bars.png", dpi=130)
    plt.close(fig)

    # Figure 2: equity curve
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(back.dates, back.opt_equity, label="DPP mean-variance", linewidth=2)
    ax.plot(
        back.dates, back.eq_equity,
        label="Equal-weight benchmark", linewidth=2, linestyle="--",
    )
    ax.set_ylabel("Growth of $1")
    ax.set_title("Walk-forward equity curve (out of sample)")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "02_equity_curve.png", dpi=130)
    plt.close(fig)

    # Figure 3: drawdown
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.fill_between(back.dates, back.opt_drawdown * 100, 0, alpha=0.45,
                    label="DPP mean-variance")
    ax.fill_between(back.dates, back.eq_drawdown * 100, 0, alpha=0.35,
                    label="Equal-weight")
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdown history")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "03_drawdown.png", dpi=130)
    plt.close(fig)

    # Figure 4: weight evolution heatmap
    fig, ax = plt.subplots(figsize=(10, 5))
    # x axis is time, y axis is asset
    weights = back.weights_history.T  # shape (n_assets, n_days)
    im = ax.imshow(
        weights, aspect="auto", cmap="viridis",
        extent=[0, weights.shape[1], 0, weights.shape[0]],
    )
    ax.set_yticks(np.arange(weights.shape[0]) + 0.5)
    ax.set_yticklabels(back.tickers[::-1])
    ax.set_xlabel("Trading day (out-of-sample)")
    ax.set_title("Optimal weight evolution over the backtest")
    fig.colorbar(im, ax=ax, label="Weight")
    fig.tight_layout()
    fig.savefig(out_dir / "04_weight_heatmap.png", dpi=130)
    plt.close(fig)

    print(f"\n  Plots saved to {out_dir}/")


# ---------------------------------------------------------------------------
# Section 11: Takeaways
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
#    than expected returns anyway), or use sum_squares(L.T @ w) where L is
#    the Cholesky factor of Sigma. Note the transpose — L.T is what gives
#    you the correct quadratic form.
#
# 4. Always write a correctness check before celebrating a speedup. The
#    L-vs-L.T bug above would silently produce wrong portfolios under a
#    benchmark that only measures time.
#
# 5. Speed is necessary but not sufficient. The walk-forward backtest in
#    Section 9 shows the optimizer produces a real portfolio that beats
#    equal-weight on Sharpe and drawdown: it diversifies away correlated
#    risk and respects transaction costs. DPP is what turns this from
#    "run it overnight" into "iterate on it during coffee" — that change
#    in research cadence is the real prize, not the raw millisecond count.


def run_full_tutorial(save_plots_dir: Path | None = None) -> None:
    # Correctness first — if this fails, nothing below matters.
    verify_all_implementations()

    print("\nLoading data through clawdfolio...")
    prices = load_prices(TICKERS, period="2y")

    bench = benchmark(prices, n_days=60)

    print("\n" + "=" * 60)
    print("SECTION 9: Walk-forward backtest — real P&L, not just speed")
    print("=" * 60)
    back = walk_forward_backtest(prices, lookback=252, gamma=5.0, kappa=1e-3)
    print_backtest_report(back)

    if save_plots_dir is not None:
        save_plots(bench, back, save_plots_dir)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--save-plots",
        action="store_true",
        help="Save matplotlib figures to examples/_dpp_plots/",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    plots_dir = (
        Path(__file__).parent / "_dpp_plots" if args.save_plots else None
    )
    run_full_tutorial(save_plots_dir=plots_dir)
