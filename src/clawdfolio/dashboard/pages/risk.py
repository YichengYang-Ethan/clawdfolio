"""Risk page: risk metrics cards and correlation heatmap."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Render the risk analysis page."""
    import plotly.express as px

    from clawdfolio.analysis.risk import analyze_risk

    st.header("Risk Analysis")

    try:
        from .overview import _get_portfolio

        portfolio = _get_portfolio()
        metrics = analyze_risk(portfolio)
    except Exception as e:
        st.error(f"Failed to compute risk metrics: {e}")
        return

    col1, col2, col3, col4 = st.columns(4)
    if metrics.volatility_annualized is not None:
        col1.metric("Volatility (Ann.)", f"{metrics.volatility_annualized*100:.1f}%")
    if metrics.beta_spy is not None:
        col2.metric("Beta (SPY)", f"{metrics.beta_spy:.2f}")
    if metrics.sharpe_ratio is not None:
        col3.metric("Sharpe Ratio", f"{metrics.sharpe_ratio:.2f}")
    if metrics.var_95 is not None:
        col4.metric("VaR 95%", f"{metrics.var_95*100:.2f}%")

    # Additional metrics
    col5, col6, col7 = st.columns(3)
    if metrics.max_drawdown is not None:
        col5.metric("Max Drawdown", f"{metrics.max_drawdown*100:.1f}%")
    if metrics.hhi is not None:
        col6.metric("HHI", f"{metrics.hhi:.3f}")
    if metrics.top_5_concentration is not None:
        col7.metric("Top-5 Weight", f"{metrics.top_5_concentration*100:.1f}%")

    # Correlation heatmap
    if metrics.high_corr_pairs:
        st.subheader("High Correlations")
        corr_data = []
        for t1, t2, corr in metrics.high_corr_pairs:
            corr_data.append({"Pair": f"{t1} - {t2}", "Correlation": corr})
        st.dataframe(corr_data, use_container_width=True)

    # Try to build a correlation matrix
    try:
        from clawdfolio.analysis.correlation import get_correlation_matrix

        tickers = [p.symbol.ticker for p in portfolio.positions[:15]]
        if len(tickers) >= 2:
            corr_matrix = get_correlation_matrix(tickers)
            if corr_matrix is not None and not corr_matrix.empty:
                st.subheader("Correlation Heatmap")
                fig = px.imshow(
                    corr_matrix,
                    text_auto=".2f",
                    color_continuous_scale="RdBu_r",
                    zmin=-1,
                    zmax=1,
                )
                fig.update_layout(margin={"t": 0, "b": 0})
                st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass
