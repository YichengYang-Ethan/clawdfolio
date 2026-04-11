"""
Spinu (2013) Risk Parity via SOCP — DRAFT
==========================================

Rough draft of the Spinu convex reformulation for equal risk contribution
(ERC) portfolios. This is the second pattern I wanted to prototype after
the DPP mean-variance tutorial; it sits at a different place in CVXPY's
cone hierarchy (exponential cone instead of pure SOC) so it's a useful
stress-test of the same ideas.

The ERC condition is

    w_i * (Sigma @ w)_i = const   for all i

which looks non-convex because w multiplies a linear function of w itself.
Spinu (2013) showed that minimizing

    (1/2) y^T Sigma y   -   sum_i b_i * log(y_i)

over y > 0 is equivalent: setting the gradient to zero gives
y_i * (Sigma y)_i = b_i, and normalizing w = y / sum(y) recovers the ERC
condition (scaled by 1/sum(y)^2). The reformulated objective is strictly
convex (quadratic-PSD plus a negative log barrier) so CVXPY returns a
unique global optimum, no iteration required.

This file is deliberately short and rough. I wanted to get the math
working and confirm the EXP-cone story before spending more time on it.
See the TODO block at the bottom for what still needs doing — the two
obvious gaps are a DPP-parametric version (matching the Cholesky pattern
from the mean-variance notebook) and a real-data walk-forward.
"""

from __future__ import annotations

import numpy as np

try:
    import cvxpy as cp
except ImportError as exc:
    raise SystemExit(
        "This example needs cvxpy. Install with: pip install cvxpy"
    ) from exc


def risk_parity_spinu(
    sigma: np.ndarray,
    budget: np.ndarray | None = None,
    solver: str = "CLARABEL",
) -> np.ndarray:
    """Solve the Spinu convex reformulation of ERC / risk budgeting.

    The formulation uses ``cp.log`` which canonicalizes to the exponential
    cone, so the solver has to support EXP. OSQP does not; CLARABEL and
    MOSEK do. This is enforced by the ``solver`` argument and demonstrated
    in :func:`demo_cone_requirement` below.
    """
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

    # Normalize back to portfolio weights. sum(y) > 0 is guaranteed by pos=True.
    return y.value / float(np.sum(y.value))


def risk_contributions(w: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """Per-asset share of total portfolio variance. Sums to 1."""
    total_var = float(w @ sigma @ w)
    if total_var <= 0:
        return np.zeros_like(w)
    return w * (sigma @ w) / total_var


def _toy_covariance(n: int = 5, seed: int = 7) -> np.ndarray:
    """Small PSD covariance with non-trivial cross-correlation."""
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((n, n))
    return a @ a.T + 0.5 * np.eye(n)


def demo_equal_risk_contribution() -> None:
    print("=" * 60)
    print("Equal Risk Contribution (ERC)")
    print("=" * 60)
    sigma = _toy_covariance(5)
    w = risk_parity_spinu(sigma)
    contribs = risk_contributions(w, sigma)
    target = np.ones(5) / 5
    print(f"  Weights:           {np.round(w, 4)}")
    print(f"  Risk contribs (%): {np.round(100 * contribs, 2)}")
    print(f"  Target  (%):       {np.round(100 * target, 2)}")
    max_err = float(np.max(np.abs(contribs - target)))
    print(f"  Max deviation from 20%: {max_err:.2e}")
    assert max_err < 1e-4, "ERC should be exact up to solver tolerance"


def demo_risk_budgeting() -> None:
    print()
    print("=" * 60)
    print("Risk Budgeting (non-equal targets)")
    print("=" * 60)
    sigma = _toy_covariance(5)
    # 40% of risk in asset 0, 15% each in assets 1..4
    budget = np.array([0.40, 0.15, 0.15, 0.15, 0.15])
    w = risk_parity_spinu(sigma, budget=budget)
    contribs = risk_contributions(w, sigma)
    print(f"  Weights:            {np.round(w, 4)}")
    print(f"  Risk contribs (%):  {np.round(100 * contribs, 2)}")
    print(f"  Target  (%):        {np.round(100 * budget, 2)}")
    max_err = float(np.max(np.abs(contribs - budget)))
    print(f"  Max deviation from target: {max_err:.2e}")
    assert max_err < 1e-4


def demo_cone_requirement() -> None:
    """Sanity-check that OSQP can't solve this (no EXP cone) while
    CLARABEL can. Not really a test, just a visible reminder for users
    who try to pass the wrong solver."""
    print()
    print("=" * 60)
    print("Solver compatibility")
    print("=" * 60)
    sigma = _toy_covariance(5)

    try:
        risk_parity_spinu(sigma, solver="OSQP")
        print("  OSQP: succeeded (unexpected — OSQP doesn't support EXP cone)")
    except Exception as exc:
        print("  OSQP: failed (expected — log barrier needs EXP cone)")
        msg = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        print(f"    {msg[:70]}")

    w = risk_parity_spinu(sigma, solver="CLARABEL")
    print(f"  CLARABEL: succeeded, sum(w) = {w.sum():.6f}")


# ----------------------------------------------------------------------
# TODO before this is ready to live in CVXPY's docs proper
# ----------------------------------------------------------------------
# - [ ] DPP-parametric version. The mean-variance tutorial shows that
#       quad_form(w, Sigma_param) is not DPP and that sum_squares(L.T @ w)
#       with L = cholesky(Sigma) is. Same trick should work here: rewrite
#       0.5 * y^T Sigma y as 0.5 * sum_squares(L_param.T @ y). The log
#       term is already DPP-compliant since b is a constant.
# - [ ] Numerical stability on ill-conditioned Sigma. The log barrier
#       blows up when any y_i drifts toward zero; need to test near
#       rank-deficient covariance matrices and document the failure mode.
# - [ ] Sanity-check against PyPortfolioOpt's HRPOpt / cyclical-descent
#       risk parity on benign covariance. Not a correctness test (their
#       approach is iterative without a convex-optimality certificate)
#       but useful to show the convex version agrees on easy inputs and
#       doesn't get stuck on hard ones.
# - [ ] Real-data walk-forward. Use Fama-French industry portfolios to
#       compare ERC against equal-weight and against the mean-variance
#       optimizer from portfolio_optimization_dpp.ipynb. Hypothesis:
#       risk parity is smoother across regime changes, so the Sharpe
#       delta vs equal-weight should be smaller but more stable.
# - [ ] API shape. If this ends up in CVXPY proper, the right surface is
#       probably something like ``cp.finance.spinu_risk_parity(sigma,
#       budget=None)`` that returns a ``cp.Problem`` the user can solve
#       themselves or combine with additional constraints. Need mentor
#       input on whether the atom returns a Problem or a Variable — the
#       Cholesky mean-variance version has the same question.


if __name__ == "__main__":
    demo_equal_risk_contribution()
    demo_risk_budgeting()
    demo_cone_requirement()
