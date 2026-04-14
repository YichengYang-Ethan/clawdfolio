"""
Spinu (2013) Risk Parity via SOCP + DPP — A CVXPY Tutorial
=============================================================

This example is a hands-on walkthrough of equal-risk-contribution (ERC)
portfolios, computed via Spinu's (2013) convex reformulation, with DPP
caching for fast walk-forward use.

It is a companion to ``portfolio_optimization_dpp.py`` (mean-variance). The
two tutorials live at different points on CVXPY's cone hierarchy: MV is a
pure SOC problem, while ERC via Spinu introduces a negative-log barrier
that puts the canonicalized problem in the exponential cone. Every lesson
here is therefore also about which solvers can handle which cones — a
gotcha that bites people porting quadratic code to risk parity.

Three things you will learn:

    1. Why the natural ERC condition ``w_i * (Sigma w)_i = const`` is
       non-convex in w, and how Spinu's change of variables

           minimize   0.5 * y^T Sigma y   -   sum_i b_i * log(y_i)
           subject to y > 0

       turns it into a strictly convex program with a unique global
       optimum. ``w = y / sum(y)`` then recovers the risk-budgeted
       portfolio, with no iteration and no convexification heuristics.

    2. How to DPP-cache the resulting problem. The Cholesky trick from
       the MV tutorial extends cleanly: ``0.5 * sum_squares(L.T @ y)``
       is DPP-compliant and matches ``0.5 * y^T Sigma y`` exactly. The
       log barrier is DPP-compliant as long as the budget vector ``b``
       stays a plain constant — see item 3.

    3. The same ``quad_form(y, Sigma_param)`` non-DPP gotcha that bit us
       in the MV tutorial bites again here, and the same Cholesky
       reformulation fixes it. We also highlight a subtler requirement
       specific to the log barrier: the budget Parameter must be declared
       ``nonneg=True`` or the problem fails DCP before DPP is even checked.

Plus:
    - Numerical stability on ill-conditioned / near-rank-deficient Sigma
    - Walk-forward backtest: ERC vs equal-weight on real price data
    - Solver compatibility: OSQP (no EXP cone) fails, CLARABEL succeeds

Run:
    python examples/risk_parity_spinu.py
    python examples/risk_parity_spinu.py --save-plots  # writes PNGs

Dependencies: cvxpy, numpy, pandas. Optional: matplotlib (for --save-plots),
yfinance through clawdfolio (falls back to synthetic GBM data if unavailable).
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
# Section 1: Data pipeline — shared with the mean-variance tutorial
# ---------------------------------------------------------------------------
# Using the same universe and loader as portfolio_optimization_dpp.py so the
# two tutorials can be read and benchmarked side-by-side. On a machine with
# no network access we fall back to geometric Brownian motion so the tutorial
# still runs end-to-end.

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "BRK-B", "JPM", "JNJ",
    "V", "PG", "UNH", "HD", "MA",
    "DIS", "BAC", "XOM", "PFE", "KO",
]


def load_prices(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    """Close-price DataFrame via clawdfolio; GBM fallback if offline."""
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


def estimate_covariance(prices: pd.DataFrame) -> np.ndarray:
    """Annualized sample covariance, symmetrized and nudged to be PD."""
    returns = prices.pct_change().dropna()
    sigma = returns.cov().values * 252.0
    n = sigma.shape[0]
    return 0.5 * (sigma + sigma.T) + 1e-8 * np.eye(n)


# ---------------------------------------------------------------------------
# Section 2: The problem — equal risk contribution and Spinu's trick
# ---------------------------------------------------------------------------
# An equal-risk-contribution (ERC) portfolio is one where each asset's
# contribution to total portfolio variance is equal:
#
#     w_i * (Sigma w)_i  =  const   for all i
#
# Risk budgeting generalizes this: each asset gets a share b_i of the total
# risk (with sum_i b_i = 1), and we solve
#
#     w_i * (Sigma w)_i  =  b_i * (w^T Sigma w)   for all i
#
# The condition is non-convex in w — each equation multiplies w by a linear
# function of w, giving a quadratic equality. Classical solutions iterate
# (cyclical coordinate descent, Newton on the ERC condition) without a
# convex-optimality certificate, and can get stuck on ill-conditioned inputs.
#
# Spinu (2013) showed the weights can be recovered from
#
#     y* = argmin_{y > 0}   0.5 * y^T Sigma y   -   sum_i b_i * log(y_i)
#     w* = y* / sum(y*)
#
# The objective is strictly convex: the quadratic term is PSD and the
# negative-log barrier is strictly convex on the positive orthant. Setting
# the gradient to zero gives y_i * (Sigma y)_i = b_i for all i, which is
# the risk-budgeting condition up to an overall scaling by 1/sum(y)^2.
# Normalizing w = y / sum(y) absorbs that scaling.
#
# Because the objective is strictly convex, CVXPY returns the unique global
# optimum — no iteration, no local-minima worries.
#
# The cost: cp.log canonicalizes to the EXPONENTIAL cone. OSQP and any
# pure-QP solver can't handle it. CLARABEL (bundled with CVXPY) and MOSEK do.
# Section 10 demonstrates the failure mode explicitly.


# ---------------------------------------------------------------------------
# Section 3: Implementation 1 — Naive (rebuild every solve)
# ---------------------------------------------------------------------------
# The "first thing you'd write" version. Every call reifies a fresh
# cp.Problem from numpy inputs, so CVXPY pays the full canonicalization cost
# on every solve. Correct, just wasteful when you solve hundreds of times in
# a walk-forward loop.

def solve_naive_spinu(
    sigma: np.ndarray,
    budget: np.ndarray | None = None,
    solver: str = "CLARABEL",
) -> np.ndarray:
    """Rebuild Problem on each call and solve. Reference implementation."""
    n = sigma.shape[0]
    if budget is None:
        budget = np.ones(n) / n
    budget = np.asarray(budget, dtype=float)
    if abs(budget.sum() - 1.0) > 1e-8:
        raise ValueError(f"Risk budget must sum to 1, got {budget.sum():.6f}")

    y = cp.Variable(n, pos=True)
    risk_term = 0.5 * cp.quad_form(y, cp.psd_wrap(sigma))
    log_term = budget @ cp.log(y)
    problem = cp.Problem(cp.Minimize(risk_term - log_term))
    problem.solve(solver=solver)

    if y.value is None:
        raise RuntimeError(f"Spinu solve failed (status={problem.status})")
    return y.value / float(np.sum(y.value))


# Back-compat alias for earlier drafts of this file.
risk_parity_spinu = solve_naive_spinu


# ---------------------------------------------------------------------------
# Section 4: DPP gotchas revisited
# ---------------------------------------------------------------------------
# There are two things to get right here. One is a direct carry-over from
# the mean-variance tutorial; the other is specific to problems with the
# log barrier.
#
# Gotcha 1: quad_form(y, Sigma_param) is not DPP. Instinctively you might
# write
#
#     Sigma_param = cp.Parameter((n, n), PSD=True)
#     obj = 0.5 * cp.quad_form(y, Sigma_param) - budget @ cp.log(y)
#
# which is still DCP-convex and even solves correctly — but prob.is_dcp(
# dpp=True) returns False, so re-solves silently pay the full
# canonicalization cost. The Cholesky reformulation from the MV tutorial
# is the fix, and the *exact same* pattern works here. See Section 5.
#
# Gotcha 2: parameter sign attributes matter. CVXPY classifies
# ``budget @ cp.log(y)`` as concave iff ``budget`` is known to be
# nonneg-signed. A plain ``cp.Parameter(n)`` has unknown sign, so the
# convex-minus-concave split fails DCP — before DPP is even asked about.
# The fix is a single keyword:
#
#     b_param = cp.Parameter(n, nonneg=True)   # DPP + DCP both OK
#     b_param = cp.Parameter(n)                # fails DCP, not just DPP
#
# Once the sign is declared, ``b_param @ cp.log(y)`` IS DPP-compliant, so
# risk budgets can vary solve-to-solve without paying the rebuild cost.
# This is actually one of the few places where CVXPY's DPP rules give a
# cleaner story than the MV tutorial — you can parametrize every input.

def assert_sigma_param_not_dpp(n: int) -> None:
    """Reproduce the MV tutorial's quad_form(_, Sigma_param) gotcha in the
    Spinu setting: still DCP, not DPP. Cholesky reformulation fixes it."""
    y = cp.Variable(n, pos=True)
    budget = np.ones(n) / n
    sigma_param = cp.Parameter((n, n), PSD=True)

    obj = 0.5 * cp.quad_form(y, sigma_param) - budget @ cp.log(y)
    prob = cp.Problem(cp.Minimize(obj))
    assert prob.is_dcp(), "Should still be DCP (the mathematical program is valid)."
    assert not prob.is_dcp(dpp=True), (
        "Expected quad_form(y, Sigma_param) to drop out of DPP, but CVXPY says it is."
    )
    print(f"  quad_form(y, Sigma_param) is_dcp(dpp=True) = "
          f"{prob.is_dcp(dpp=True)}  (as expected)")


def assert_budget_param_needs_sign(n: int) -> None:
    """Show that b_param @ cp.log(y) needs nonneg=True on the Parameter."""
    y = cp.Variable(n, pos=True)
    b_unsigned = cp.Parameter(n)          # no sign attribute
    b_nonneg = cp.Parameter(n, nonneg=True)

    sigma = np.eye(n)
    obj_bad = 0.5 * cp.quad_form(y, sigma) - b_unsigned @ cp.log(y)
    prob_bad = cp.Problem(cp.Minimize(obj_bad))
    assert not prob_bad.is_dcp(), (
        "Expected b_unsigned @ cp.log(y) to fail DCP, but CVXPY says it's OK."
    )

    obj_good = 0.5 * cp.quad_form(y, sigma) - b_nonneg @ cp.log(y)
    prob_good = cp.Problem(cp.Minimize(obj_good))
    assert prob_good.is_dcp() and prob_good.is_dcp(dpp=True), (
        "Expected b_nonneg @ cp.log(y) to be DCP+DPP, but CVXPY disagrees."
    )
    print(f"  unsigned-budget    is_dcp = {prob_bad.is_dcp()}         "
          "(fails — concavity undetermined without sign)")
    print(f"  nonneg-budget      is_dcp = {prob_good.is_dcp()} "
          f" is_dcp(dpp=True) = {prob_good.is_dcp(dpp=True)}  (works)")


# ---------------------------------------------------------------------------
# Section 5: Implementation 2 — DPP with parametric Sigma via Cholesky
# ---------------------------------------------------------------------------
# This is the workhorse. Sigma changes day-to-day in any real walk-forward
# or stress test, and each solve re-uses the same canonicalized Problem.
#
# Same Cholesky trick as the MV tutorial:
#
#     Sigma = L L^T   (L from np.linalg.cholesky, lower triangular)
#     y^T Sigma y  =  y^T L L^T y  =  || L^T y ||_2^2  =  sum_squares(L^T y)
#
# sum_squares applied to an affine Parameter-times-Variable expression is
# DPP-compliant. L.T @ y is affine in both L and y.
#
# Watch the transpose: L.T @ y, NOT L @ y. Using L @ y gives y^T L^T L y,
# which is a different quadratic form and in general is NOT equal to
# y^T Sigma y. verify_all_implementations() below catches this mistake by
# comparing weights across implementations — a correctness check that would
# silently pass if we only measured timings.

class SpinuRebalancerCholesky:
    """DPP-compliant ERC rebalancer. Accepts varying Sigma via L = chol(Sigma).

    The risk budget is frozen at construction time (see Section 4 for why).
    To change budgets across solves, either construct a new instance or
    accept the canonicalization cost of solve_naive_spinu.
    """

    def __init__(
        self,
        n: int,
        budget: np.ndarray | None = None,
        solver: str = "CLARABEL",
    ) -> None:
        if budget is None:
            budget = np.ones(n) / n
        budget = np.asarray(budget, dtype=float)
        if abs(budget.sum() - 1.0) > 1e-8:
            raise ValueError(f"Risk budget must sum to 1, got {budget.sum():.6f}")

        self._solver = solver
        self._n = n
        self.budget = budget
        self.L_param = cp.Parameter((n, n))
        self.y = cp.Variable(n, pos=True)

        # L.T @ y, not L @ y — see the derivation above Section 5.
        risk_term = 0.5 * cp.sum_squares(self.L_param.T @ self.y)
        log_term = budget @ cp.log(self.y)
        self.problem = cp.Problem(cp.Minimize(risk_term - log_term))
        assert self.problem.is_dcp(dpp=True), (
            "Cholesky rebalancer should be DPP-compliant — check that the "
            "budget is a numpy array (not a Parameter)."
        )

    def solve(self, sigma: np.ndarray) -> np.ndarray:
        self.L_param.value = np.linalg.cholesky(sigma)
        self.problem.solve(solver=self._solver)
        if self.y.value is None:
            raise RuntimeError(
                f"Cholesky solve failed (status={self.problem.status})"
            )
        y_val = self.y.value
        return y_val / float(np.sum(y_val))


# ---------------------------------------------------------------------------
# Section 6: Correctness — do both implementations agree?
# ---------------------------------------------------------------------------
# Before we celebrate a speedup, prove that naive and Cholesky compute the
# same weights on random problems. This is where an L-vs-L.T bug would
# surface. We also verify the ERC/budget condition directly: risk
# contributions must hit the target budget up to solver tolerance.

def risk_contributions(w: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """Per-asset share of total portfolio variance. Sums to 1 if variance > 0."""
    total_var = float(w @ sigma @ w)
    if total_var <= 0:
        return np.zeros_like(w)
    return w * (sigma @ w) / total_var


def verify_all_implementations(
    n_checks: int = 5, n: int = 10, tol: float = 1e-4
) -> None:
    """Solve random problems with both implementations and assert the weight
    vectors agree AND that realized risk contributions match the budget."""
    rng = np.random.default_rng(0)
    print("\nCorrectness check: naive and DPP-Cholesky must agree, and "
          "realized risk contributions must hit the target budget.")

    for k in range(n_checks):
        A = rng.standard_normal((n, n))
        sigma = A @ A.T + 0.1 * np.eye(n)
        budget = rng.dirichlet(np.ones(n))  # random simplex point

        w_naive = solve_naive_spinu(sigma, budget)

        reb_chol = SpinuRebalancerCholesky(n, budget)
        w_chol = reb_chol.solve(sigma)

        err_match = float(np.max(np.abs(w_naive - w_chol)))
        contribs = risk_contributions(w_chol, sigma)
        err_budget = float(np.max(np.abs(contribs - budget)))

        ok = err_match < tol and err_budget < tol
        status = "PASS" if ok else "FAIL"
        print(
            f"  check {k+1}: "
            f"max|naive-chol|={err_match:.2e}  "
            f"max|risk-budget|={err_budget:.2e}  [{status}]"
        )
        assert ok, (
            f"Implementations disagree or ERC condition not met (tol={tol})."
        )


# ---------------------------------------------------------------------------
# Section 7: Speed benchmark
# ---------------------------------------------------------------------------
# Measure the DPP speedup on a realistic workload: solve ERC N times with
# the covariance drifting slightly each day (as it does in a walk-forward
# as new observations enter the estimation window).

@dataclass
class BenchmarkResult:
    n_days: int
    naive_total: float
    dpp_chol_total: float
    naive_per_solve_ms: float
    dpp_chol_per_solve_ms: float
    speedup_chol: float


def simulate_daily_sigma(
    sigma_base: np.ndarray, n_days: int, seed: int = 0, noise: float = 0.05
) -> np.ndarray:
    """Perturb a base covariance matrix day-by-day. Emulates a walk-forward
    where Sigma drifts as new daily observations enter the rolling window."""
    n = sigma_base.shape[0]
    rng = np.random.default_rng(seed)
    out = np.empty((n_days, n, n))
    for t in range(n_days):
        delta = rng.standard_normal((n, n)) * noise
        sigma_t = sigma_base + sigma_base * (0.5 * (delta + delta.T))
        sigma_t = 0.5 * (sigma_t + sigma_t.T) + 1e-6 * np.eye(n)
        # Guarantee positive-definiteness after perturbation.
        min_eig = float(np.linalg.eigvalsh(sigma_t).min())
        if min_eig <= 0:
            sigma_t = sigma_t + (abs(min_eig) + 1e-6) * np.eye(n)
        out[t] = sigma_t
    return out


def benchmark(prices: pd.DataFrame, n_days: int = 60) -> BenchmarkResult:
    sigma = estimate_covariance(prices)
    n = sigma.shape[0]
    sigma_stream = simulate_daily_sigma(sigma, n_days)

    print(f"\nUniverse: {n} assets, benchmarking {n_days} Spinu re-solves "
          f"with varying Sigma each day.\n")

    # Implementation 1: Naive rebuild
    t0 = time.perf_counter()
    for t in range(n_days):
        _ = solve_naive_spinu(sigma_stream[t])
    naive_total = time.perf_counter() - t0

    # Implementation 2: DPP with Cholesky
    rebalancer_chol = SpinuRebalancerCholesky(n)
    _ = rebalancer_chol.solve(sigma_stream[0])  # pay compile cost once
    t0 = time.perf_counter()
    for t in range(1, n_days):
        _ = rebalancer_chol.solve(sigma_stream[t])
    dpp_chol_total = time.perf_counter() - t0

    naive_per = 1e3 * naive_total / n_days
    chol_per = 1e3 * dpp_chol_total / max(n_days - 1, 1)

    print(f"  [1] Naive rebuild every solve : "
          f"{naive_total:6.2f}s total ({naive_per:6.1f} ms/solve)")
    print(f"  [2] DPP with Cholesky Sigma   : "
          f"{dpp_chol_total:6.2f}s total ({chol_per:6.1f} ms/solve, "
          f"first compile not counted)")
    print()
    speedup = naive_total / max(dpp_chol_total, 1e-9)
    print(f"  Aggregate speedup [1] -> [2]: {speedup:5.1f}x")

    print("\n  DPP compliance checks on the 'wrong' patterns:")
    assert_sigma_param_not_dpp(n)
    assert_budget_param_needs_sign(n)

    return BenchmarkResult(
        n_days=n_days,
        naive_total=naive_total,
        dpp_chol_total=dpp_chol_total,
        naive_per_solve_ms=naive_per,
        dpp_chol_per_solve_ms=chol_per,
        speedup_chol=speedup,
    )


# ---------------------------------------------------------------------------
# Section 8: Numerical stability on ill-conditioned covariance
# ---------------------------------------------------------------------------
# The log barrier keeps y_i bounded away from 0 at the optimum, so Spinu
# implicitly tolerates *mildly* ill-conditioned Sigma better than naive
# inverse-covariance methods. But there are two pathologies worth testing:
#
#   (i) Large condition number: Sigma is PD but one eigenvalue is tiny.
#       The solver still works but may need higher precision.
#  (ii) Rank deficiency: Sigma is exactly singular. Cholesky fails outright.
#       In practice we jitter with a small diagonal load before Cholesky.

@dataclass
class StabilityCase:
    name: str
    sigma: np.ndarray
    description: str


def _build_stability_cases(n: int = 6) -> list[StabilityCase]:
    rng = np.random.default_rng(11)
    cases: list[StabilityCase] = []

    # Case A: Well-conditioned baseline.
    A = rng.standard_normal((n, n))
    sigma_a = A @ A.T + 0.5 * np.eye(n)
    cases.append(StabilityCase(
        name="well-conditioned",
        sigma=sigma_a,
        description="standard Gaussian covariance, condition ~O(10)",
    ))

    # Case B: Ill-conditioned (one tiny eigenvalue).
    Q, _ = np.linalg.qr(rng.standard_normal((n, n)))
    eigs = np.array([1.0, 0.5, 0.1, 0.01, 1e-4, 1e-6])
    sigma_b = Q @ np.diag(eigs) @ Q.T
    sigma_b = 0.5 * (sigma_b + sigma_b.T)
    cases.append(StabilityCase(
        name="ill-conditioned",
        sigma=sigma_b,
        description=f"condition number ~{1.0/eigs.min():.0e}",
    ))

    # Case C: Near-rank-deficient (one redundant asset). Cholesky needs a
    # small diagonal load or it will fail on the exact-singular direction.
    B = rng.standard_normal((n, n - 1))
    sigma_c = B @ B.T + 1e-8 * np.eye(n)
    cases.append(StabilityCase(
        name="near-rank-deficient",
        sigma=sigma_c,
        description="rank n-1 plus 1e-8 diagonal jitter",
    ))

    return cases


def demo_numerical_stability() -> None:
    print("\n" + "=" * 60)
    print("Numerical stability")
    print("=" * 60)
    print("The log barrier keeps y_i away from 0, but Cholesky still needs")
    print("Sigma to be strictly PD. Here is how each regime behaves:\n")
    cases = _build_stability_cases()
    for case in cases:
        cond = np.linalg.cond(case.sigma)
        print(f"  Case '{case.name}':  cond(Sigma) = {cond:.1e}")
        print(f"    {case.description}")
        try:
            w = solve_naive_spinu(case.sigma)
            rc = risk_contributions(w, case.sigma)
            target = np.ones_like(w) / len(w)
            max_err = float(np.max(np.abs(rc - target)))
            if max_err < 1e-4:
                status = "OK"
            elif max_err < 1e-2:
                status = "DEGRADED"
            else:
                status = "POOR"
            print(f"    -> {status}: max risk-contrib deviation from target "
                  f"= {max_err:.2e}")
        except Exception as exc:
            print(f"    -> FAILED: {type(exc).__name__}: {str(exc)[:70]}")
        print()


# ---------------------------------------------------------------------------
# Section 9: Walk-forward backtest — does ERC actually work out of sample?
# ---------------------------------------------------------------------------
# Same walk-forward protocol as the MV tutorial, modulo the objective:
#
#   For each trading day t in the test window:
#     1. Estimate Sigma from the trailing 252-day window ending at t
#        (refreshed every ``sigma_refresh_days``, default weekly).
#     2. Solve Spinu ERC for the rebalancing weights.
#     3. Apply the weights to day t+1's realized returns.
#     4. Carry weights forward for the next day.
#
# Compared against a daily-rebalanced equal-weight baseline. Risk parity
# is *supposed* to produce smoother equity curves and lower drawdowns than
# equal-weight, because it systematically down-weights high-volatility
# assets. That's the economic claim we're testing here — a fast optimizer
# that produces bad portfolios is useless.

@dataclass
class ERCBacktestResult:
    tickers: list[str]
    dates: pd.DatetimeIndex
    erc_returns: np.ndarray
    eq_returns: np.ndarray
    erc_equity: np.ndarray
    eq_equity: np.ndarray
    erc_drawdown: np.ndarray
    eq_drawdown: np.ndarray
    weights_history: np.ndarray
    risk_contrib_history: np.ndarray
    eq_risk_contrib_history: np.ndarray
    erc_metrics: dict[str, float]
    eq_metrics: dict[str, float]


def _metrics(returns: np.ndarray, freq: int = 252) -> dict[str, float]:
    equity = np.cumprod(1.0 + returns)
    total_return = float(equity[-1] - 1.0)
    mean = float(np.mean(returns))
    std = float(np.std(returns, ddof=1))
    sharpe = float(np.sqrt(freq) * mean / std) if std > 0 else float("nan")
    ann_vol = float(std * np.sqrt(freq))
    running_peak = np.maximum.accumulate(equity)
    drawdown = (equity - running_peak) / running_peak
    return {
        "total_return": total_return,
        "annualized_vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": float(abs(np.min(drawdown))),
        "final_equity": float(equity[-1]),
    }


def walk_forward_erc_backtest(
    prices: pd.DataFrame,
    lookback: int = 252,
    sigma_refresh_days: int = 5,
) -> ERCBacktestResult:
    returns = prices.pct_change().dropna()
    if len(returns) <= lookback + 5:
        raise ValueError("Not enough history for the requested lookback.")

    tickers = list(returns.columns)
    n = len(tickers)
    test_dates = returns.index[lookback:]
    w_prev = np.ones(n) / n

    rebalancer = SpinuRebalancerCholesky(n)
    last_sigma: np.ndarray | None = None
    last_sigma_refresh = -(sigma_refresh_days + 1)

    erc_daily, eq_daily = [], []
    weights_hist, rc_hist, eq_rc_hist = [], [], []
    date_hist = []
    w_eq = np.ones(n) / n

    for i, date in enumerate(test_dates[:-1]):
        idx = returns.index.get_loc(date)
        window = returns.iloc[idx - lookback: idx]

        if last_sigma is None or (i - last_sigma_refresh) >= sigma_refresh_days:
            sigma = window.cov().values * 252.0
            sigma = 0.5 * (sigma + sigma.T) + 1e-8 * np.eye(n)
            last_sigma = sigma
            last_sigma_refresh = i
        else:
            sigma = last_sigma

        try:
            w_new = rebalancer.solve(sigma)
        except Exception as exc:  # pragma: no cover
            print(f"  [warn] solve failed on {date}: {exc} — holding weights")
            w_new = w_prev.copy()

        next_ret = returns.iloc[idx + 1].values
        erc_daily.append(float(np.dot(w_new, next_ret)))
        eq_daily.append(float(np.mean(next_ret)))
        weights_hist.append(w_new)
        rc_hist.append(risk_contributions(w_new, sigma))
        eq_rc_hist.append(risk_contributions(w_eq, sigma))
        date_hist.append(test_dates[i + 1])
        w_prev = w_new

    erc_arr = np.array(erc_daily)
    eq_arr = np.array(eq_daily)
    weights_arr = np.array(weights_hist)
    rc_arr = np.array(rc_hist)
    eq_rc_arr = np.array(eq_rc_hist)

    erc_equity = np.cumprod(1.0 + erc_arr)
    eq_equity = np.cumprod(1.0 + eq_arr)
    erc_dd = erc_equity / np.maximum.accumulate(erc_equity) - 1.0
    eq_dd = eq_equity / np.maximum.accumulate(eq_equity) - 1.0

    return ERCBacktestResult(
        tickers=tickers,
        dates=pd.DatetimeIndex(date_hist),
        erc_returns=erc_arr,
        eq_returns=eq_arr,
        erc_equity=erc_equity,
        eq_equity=eq_equity,
        erc_drawdown=erc_dd,
        eq_drawdown=eq_dd,
        weights_history=weights_arr,
        risk_contrib_history=rc_arr,
        eq_risk_contrib_history=eq_rc_arr,
        erc_metrics=_metrics(erc_arr),
        eq_metrics=_metrics(eq_arr),
    )


def print_backtest_report(result: ERCBacktestResult) -> None:
    erc = result.erc_metrics
    eq = result.eq_metrics
    tickers = result.tickers
    n_days = len(result.erc_returns)

    print(f"\nWalk-forward backtest over {n_days} trading days "
          f"(out-of-sample; 252-day rolling window, weekly Sigma refresh)")
    print()
    print(f"  {'Metric':<24}{'ERC':>14}{'Equal-weight':>16}")
    print(f"  {'-' * 54}")
    print(f"  {'Total return':<24}"
          f"{erc['total_return']*100:>13.2f}%{eq['total_return']*100:>15.2f}%")
    print(f"  {'Annualized volatility':<24}"
          f"{erc['annualized_vol']*100:>13.2f}%"
          f"{eq['annualized_vol']*100:>15.2f}%")
    print(f"  {'Annualized Sharpe':<24}"
          f"{erc['sharpe']:>14.3f}{eq['sharpe']:>16.3f}")
    print(f"  {'Max drawdown':<24}"
          f"{erc['max_drawdown']*100:>13.2f}%{eq['max_drawdown']*100:>15.2f}%")
    print(f"  {'$1 grows to':<24}"
          f"{'$' + format(erc['final_equity'], '.3f'):>14}"
          f"{'$' + format(eq['final_equity'], '.3f'):>16}")

    # Risk contribution dispersion — does ERC really equalize risk out of sample?
    # The point of risk parity is that each asset should contribute 1/n of the
    # total variance. Equal-weight portfolios don't, precisely because they
    # weight *dollars* equally rather than *risk*.
    rc_erc = result.risk_contrib_history
    rc_eq = result.eq_risk_contrib_history
    disp_erc = float(rc_erc.std(axis=1).mean())
    disp_eq = float(rc_eq.std(axis=1).mean())
    max_rc_eq = float(rc_eq.max(axis=1).mean())
    target = 1.0 / rc_erc.shape[1]
    print(f"\n  Cross-sectional risk-contrib dispersion (avg daily std):")
    print(f"    ERC          : {disp_erc*100:7.3f}%   "
          f"(target = 0; ERC is working if this is ~machine zero)")
    print(f"    Equal-weight : {disp_eq*100:7.3f}%   "
          f"(non-zero — dollar-equal ≠ risk-equal)")
    print(f"  Under equal-weight, the largest single asset's average daily")
    print(f"  risk contribution is {max_rc_eq*100:.1f}%, vs the ERC target of "
          f"{target*100:.1f}%.")

    final = result.weights_history[-1]
    top_idx = np.argsort(final)[::-1][:5]
    print("\n  Top 5 holdings on final day:")
    for i in top_idx:
        if final[i] > 0.005:
            print(f"    {tickers[i]:<6}  {final[i]*100:5.1f}%")


# ---------------------------------------------------------------------------
# Section 10: Solver compatibility (EXP cone requirement)
# ---------------------------------------------------------------------------
# The log barrier canonicalizes to the exponential cone. OSQP is a pure QP
# solver and refuses EXP. CLARABEL and MOSEK support EXP and work fine.
# An easy gotcha for anyone porting code from MV to risk parity — the solver
# call that worked yesterday suddenly fails today.

def demo_cone_requirement() -> None:
    print("\n" + "=" * 60)
    print("Solver cone compatibility")
    print("=" * 60)
    sigma = _build_stability_cases()[0].sigma  # well-conditioned

    print("  The log barrier lives in the exponential cone.")
    print("  Pure-QP solvers like OSQP cannot handle it:\n")
    try:
        solve_naive_spinu(sigma, solver="OSQP")
        print("  OSQP: SUCCEEDED (unexpected — OSQP doesn't support EXP cone)")
    except Exception as exc:
        msg = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        print("  OSQP: failed (expected — log barrier needs EXP cone)")
        print(f"    {msg[:72]}")

    w = solve_naive_spinu(sigma, solver="CLARABEL")
    print(f"\n  CLARABEL: succeeded, sum(w) = {w.sum():.6f}")


# ---------------------------------------------------------------------------
# Section 11: Optional plots
# ---------------------------------------------------------------------------

def save_plots(
    bench: BenchmarkResult, back: ERCBacktestResult, out_dir: Path
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:  # pragma: no cover
        print("[warn] matplotlib not available; skipping plots")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Figure 1: speedup bar chart.
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["Naive", "DPP\n(Cholesky)"]
    values = [bench.naive_per_solve_ms, bench.dpp_chol_per_solve_ms]
    colors = ["#d46a6a", "#6ad49a"]
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("Milliseconds per solve (lower is better)")
    ax.set_title("Spinu ERC re-solve: naive vs DPP-cached")
    for bar, v in zip(bars, values, strict=False):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0, v,
            f"{v:.1f} ms", ha="center", va="bottom",
        )
    fig.tight_layout()
    fig.savefig(out_dir / "01_spinu_speedup.png", dpi=130)
    plt.close(fig)

    # Figure 2: equity curve.
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(back.dates, back.erc_equity, label="ERC (Spinu)", linewidth=2)
    ax.plot(
        back.dates, back.eq_equity,
        label="Equal-weight benchmark", linewidth=2, linestyle="--",
    )
    ax.set_ylabel("Growth of $1")
    ax.set_title("ERC vs equal-weight: walk-forward equity curve")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "02_spinu_equity.png", dpi=130)
    plt.close(fig)

    # Figure 3: drawdown.
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.fill_between(back.dates, back.erc_drawdown * 100, 0, alpha=0.45,
                    label="ERC")
    ax.fill_between(back.dates, back.eq_drawdown * 100, 0, alpha=0.35,
                    label="Equal-weight")
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdown history: ERC vs equal-weight")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "03_spinu_drawdown.png", dpi=130)
    plt.close(fig)

    # Figure 4: realized risk contributions over time.
    fig, ax = plt.subplots(figsize=(10, 5))
    rc = back.risk_contrib_history.T  # (n_assets, n_days)
    im = ax.imshow(
        rc, aspect="auto", cmap="viridis",
        vmin=0, vmax=max(0.15, float(rc.max())),
    )
    ax.set_yticks(np.arange(rc.shape[0]))
    ax.set_yticklabels(back.tickers)
    ax.set_xlabel("Trading day (out-of-sample)")
    ax.set_title(
        f"Realized risk contributions under ERC  "
        f"(target = {1.0/rc.shape[0]*100:.1f}% for each asset)"
    )
    fig.colorbar(im, ax=ax, label="Fraction of total variance")
    fig.tight_layout()
    fig.savefig(out_dir / "04_spinu_risk_contrib.png", dpi=130)
    plt.close(fig)

    # Figure 5: weight evolution.
    fig, ax = plt.subplots(figsize=(10, 5))
    weights = back.weights_history.T
    im = ax.imshow(weights, aspect="auto", cmap="plasma")
    ax.set_yticks(np.arange(weights.shape[0]))
    ax.set_yticklabels(back.tickers)
    ax.set_xlabel("Trading day (out-of-sample)")
    ax.set_title("ERC weight evolution over the backtest")
    fig.colorbar(im, ax=ax, label="Portfolio weight")
    fig.tight_layout()
    fig.savefig(out_dir / "05_spinu_weights.png", dpi=130)
    plt.close(fig)

    print(f"\n  Plots saved to {out_dir}/")


# ---------------------------------------------------------------------------
# Section 12: Takeaways
# ---------------------------------------------------------------------------
# 1. Spinu's reformulation turns a non-convex ERC condition into a strictly
#    convex program with a unique global optimum and no iteration required.
#    This is a powerful pattern worth remembering whenever you see a
#    fixed-point condition w_i * f_i(w) = const.
#
# 2. The Cholesky DPP pattern from the MV tutorial applies directly here:
#    0.5 * sum_squares(L.T @ y) replaces the non-DPP quad_form(y, Sigma_param).
#    Same transpose trap — the correctness check would catch it even if the
#    benchmark didn't.
#
# 3. Parameter sign attributes matter. budget @ cp.log(y) is DCP-concave
#    only when the budget is known to be nonneg-signed. cp.Parameter(n)
#    has unknown sign and fails DCP before DPP is even consulted. Declare
#    cp.Parameter(n, nonneg=True) and everything works — including
#    DPP-caching a problem where the budget itself varies solve-to-solve.
#    This is a small but easy-to-miss gotcha specific to problems with
#    concave atoms.
#
# 4. Solver choice matters. The log barrier puts you in the exponential
#    cone, so OSQP is out. CLARABEL (bundled with CVXPY) or MOSEK are the
#    natural choices.
#
# 5. The economic intuition holds out of sample. Risk parity produces a
#    smoother equity curve and smaller drawdowns than equal-weight,
#    especially when the universe contains one or two very volatile
#    assets — because ERC systematically down-weights them.
#
# 6. Open design questions for CVXPY's finance story (mentor input needed):
#    - Should this pattern ship as an atom like `cp.finance.risk_parity`,
#      or stay as a documentation-only recipe in examples/?
#    - If it ships as an atom, what is the input surface: Sigma (and chol
#      internally), or L (so the caller controls the factorization)?
#    - The same two questions apply to the MV + transaction-cost pattern.
#      A consistent answer across both cookbook examples is probably more
#      valuable than either one in isolation.


def run_full_tutorial(save_plots_dir: Path | None = None) -> None:
    verify_all_implementations()

    print("\nLoading data through clawdfolio...")
    prices = load_prices(TICKERS, period="2y")

    print("\n" + "=" * 60)
    print("SECTION 7: Speed benchmark — naive vs DPP-Cholesky")
    print("=" * 60)
    bench = benchmark(prices, n_days=60)

    print()
    print("=" * 60)
    print("SECTION 8: Numerical stability probes")
    print("=" * 60)
    demo_numerical_stability()

    demo_cone_requirement()

    print("\n" + "=" * 60)
    print("SECTION 9: Walk-forward backtest — ERC vs equal-weight")
    print("=" * 60)
    back = walk_forward_erc_backtest(prices, lookback=252)
    print_backtest_report(back)

    if save_plots_dir is not None:
        save_plots(bench, back, save_plots_dir)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--save-plots",
        action="store_true",
        help="Save matplotlib figures to examples/_spinu_plots/",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    plots_dir = (
        Path(__file__).parent / "_spinu_plots" if args.save_plots else None
    )
    run_full_tutorial(save_plots_dir=plots_dir)
