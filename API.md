# Clawdfolio Python API Reference

## Core Types

```python
from clawdfolio import Symbol, Position, Quote, Portfolio, RiskMetrics, Alert
from clawdfolio import Config, load_config
from clawdfolio.core.types import Exchange, AlertType, AlertSeverity
```

## Brokers

```python
from clawdfolio.brokers import get_broker, list_brokers, BaseBroker

broker = get_broker("longport")      # or "futu", "demo", "all"
with broker:
    portfolio = broker.get_portfolio()
    quote = broker.get_quote(Symbol(ticker="AAPL"))
```

Custom brokers: subclass `BaseBroker` and use `@register_broker("name")`.

## Risk Analysis

```python
from clawdfolio.analysis.risk import (
    analyze_risk,                    # Full analysis -> RiskMetrics
    calculate_volatility,
    calculate_beta,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_var,
    calculate_cvar,
    calculate_max_drawdown,
    calculate_correlation_matrix,
)

metrics = analyze_risk(portfolio)
print(metrics.sharpe_ratio, metrics.sortino_ratio)
print(metrics.var_95, metrics.cvar_95)
```

## Technical Indicators

```python
from clawdfolio.analysis.technical import (
    calculate_rsi,                   # Wilder-smoothed RSI (scalar)
    calculate_rsi_series,            # Full RSI series
    calculate_sma, calculate_ema,
    calculate_bollinger_bands,
    calculate_macd,
    detect_rsi_extremes,
    is_golden_cross, is_death_cross,
)
```

## Market Data

```python
from clawdfolio.market import (
    get_price, get_history, get_history_multi,
    get_quotes_yfinance, get_news, get_earnings_date,
    get_option_quote, get_option_chain, get_option_expiries,
    is_market_open, get_market_status, is_trading_day,
    risk_free_rate,
)
```

## Trading Calendar

```python
from clawdfolio.market import is_trading_day, next_trading_day, trading_days_between
```

Algorithmic US holiday generation (NYSE rules). Hardcoded 2024-2027 fast-path cache.

## DCA Strategy

```python
from clawdfolio.strategies.dca import (
    DCAStrategy, check_dca_signals, calculate_dca_performance,
)

strategy = DCAStrategy(targets={"AAPL": 0.30, "MSFT": 0.20}, monthly_amount=2000)
signals = strategy.check_signals(portfolio)
alloc = strategy.get_regular_allocation()
perf = calculate_dca_performance("AAPL", monthly_amount=1000, months=12)
```

## Export

```python
from clawdfolio.output import (
    export_portfolio_csv, export_portfolio_json,
    export_risk_csv, export_risk_json,
    export_alerts_csv, export_alerts_json,
)

csv_str = export_portfolio_csv(portfolio)
json_str = export_risk_json(metrics)
```
