# Clawdfolio 🦙📊

[![CI](https://github.com/YichengYang-Ethan/clawdfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/YichengYang-Ethan/clawdfolio/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/YichengYang-Ethan/clawdfolio/branch/main/graph/badge.svg)](https://codecov.io/gh/YichengYang-Ethan/clawdfolio)
[![PyPI](https://img.shields.io/pypi/v/clawdfolio.svg)](https://pypi.org/project/clawdfolio/)
[![Downloads](https://static.pepy.tech/badge/clawdfolio/month)](https://pepy.tech/project/clawdfolio)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

English | [中文](README_CN.md)

> **Production-grade quantitative portfolio toolkit** — multi-broker aggregation, institutional risk analytics, portfolio rebalancing, options lifecycle management, and 20+ automated finance workflows.

---

## Why Clawdfolio?

| Traditional Tools | Clawdfolio |
|-------------------|------------|
| Manual data entry | Auto-sync from Longport, Moomoo/Futu |
| Basic P&L tracking | VaR, Sharpe, Beta, Max Drawdown, HHI |
| Single broker view | Multi-broker aggregation |
| Spreadsheet alerts | Smart RSI / price / P&L alerts |
| No rebalancing | Target allocation tracking + DCA proposals |
| No extensibility | Python API + CLI + Streamlit dashboard |

---

## Features

### Core Portfolio Management
- **Multi-Broker Support** — Longport (Longbridge), Moomoo/Futu, or demo mode
- **Portfolio History** — Snapshot tracking, NAV curves, performance metrics over time
- **Portfolio Rebalancing** — Target allocation deviations, DCA-aware rebalance proposals
- **Smart Alerts** — Price movements, RSI extremes, P&L thresholds with notification support

### Risk & Analytics
- **Risk Analytics** — Volatility, Beta, Sharpe/Sortino, VaR/CVaR, Max Drawdown, GARCH forecasting
- **Concentration Analysis** — HHI index, sector exposure, correlation warnings
- **Stress Testing** — 5 historical scenarios (COVID crash, 2022 bear, etc.) with leveraged ETF awareness
- **Technical Analysis** — RSI, SMA, EMA, Bollinger Bands
- **Fama-French Factors** — 3-factor exposure analysis with alpha estimation

### Options & Strategies
- **Options Toolkit** — Real-time Greeks, option chain snapshots, buyback trigger monitor
- **Bubble Risk Score** — Composite market risk indicator ([Market-Bubble-Index-Dashboard](https://github.com/YichengYang-Ethan/Market-Bubble-Index-Dashboard))
- **Risk-Driven Covered Call** — Backtested 11 years: **83% win rate**, **+3.0% annualized alpha**

### Automation
- **20+ Finance Workflows** — Reports, alerts, market intel, broker snapshots
- **Earnings Calendar** — Track upcoming earnings for holdings
- **Dashboard** — Streamlit-powered interactive dashboard

---

## Quick Start

### Installation

```bash
pip install clawdfolio                  # Core (demo broker included)
pip install clawdfolio[longport]        # + Longport broker
pip install clawdfolio[futu]            # + Moomoo/Futu broker
pip install clawdfolio[all]             # Everything
```

### CLI

```bash
# Portfolio
clawdfolio summary                     # Portfolio overview
clawdfolio summary --broker demo       # Use demo broker
clawdfolio risk --detailed             # Risk metrics with RSI, sectors, GARCH

# Market data
clawdfolio quotes AAPL TSLA NVDA       # Real-time quotes
clawdfolio alerts                      # Check alerts
clawdfolio earnings                    # Upcoming earnings calendar

# History & rebalancing
clawdfolio history snapshot            # Save portfolio snapshot
clawdfolio history show --days 30      # View NAV history
clawdfolio history performance         # Performance metrics
clawdfolio rebalance check             # Check target deviations
clawdfolio rebalance propose --amount 5000  # DCA allocation proposal

# Analysis
clawdfolio dca AAPL --months 12        # DCA backtest
clawdfolio stress                      # Stress test scenarios
clawdfolio factors                     # Fama-French factor exposure
clawdfolio bubble                      # Market bubble index

# Options
clawdfolio options expiries TQQQ
clawdfolio options quote TQQQ --expiry 2026-06-18 --strike 60 --type C
clawdfolio options chain TQQQ --expiry 2026-06-18

# Dashboard
clawdfolio dashboard                   # Launch Streamlit dashboard
```

**Example output** (`clawdfolio summary --broker demo`):

```
╭──────────────────────── Portfolio Summary ────────────────────────╮
│ Net Assets: $100,153.87                                          │
│ Cash: $15,000.00                                                 │
│ Market Value: $85,153.87                                         │
│ Day P&L: +$556.88 (+0.56%)                                       │
╰──────────────────────────────────────────────────────────────────╯
┏━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ Ticker ┃ Weight ┃ Shares ┃   Price ┃   Value ┃ Day P&L ┃ Total P&L ┃
┡━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ SPY    │  21.1% │     40 │ $527.38 │ $21,095 │   +$399 │     +$495 │
│ NVDA   │  12.1% │     25 │ $485.99 │ $12,150 │   +$210 │   +$1,650 │
│ MSFT   │  11.2% │     30 │ $374.17 │ $11,225 │   $-125 │     +$125 │
│ QQQ    │  10.9% │     25 │ $435.49 │ $10,887 │    $-70 │      +$12 │
│ AAPL   │   8.7% │     50 │ $173.79 │  $8,689 │    $-42 │     +$289 │
│ ...    │        │        │         │         │         │           │
└────────┴────────┴────────┴─────────┴─────────┴─────────┴───────────┘
```

> Flags like `--broker`, `--output`, `--config` work before or after the subcommand:
> `clawdfolio --broker demo summary` and `clawdfolio summary --broker demo` are equivalent.

### Python API

```python
from clawdfolio.brokers import get_broker
from clawdfolio.analysis import analyze_risk

broker = get_broker("demo")  # or "longport", "futu"
broker.connect()

portfolio = broker.get_portfolio()
metrics = analyze_risk(portfolio)

print(f"Net Assets: ${portfolio.net_assets:,.2f}")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"VaR 95%: {metrics.var_95:.2%}")
```

---

## Risk Metrics

| Metric | Description |
|--------|-------------|
| **Volatility** | 20-day and 60-day annualized, GARCH(1,1) forecast |
| **Beta** | Correlation with SPY/QQQ benchmarks |
| **Sharpe Ratio** | Risk-adjusted returns |
| **Sortino Ratio** | Downside-only risk-adjusted returns |
| **VaR / CVaR** | Value at Risk (95%/99%) + Expected Shortfall |
| **Max Drawdown** | Largest peak-to-trough decline |
| **HHI** | Portfolio concentration index |
| **Stress Testing** | COVID-19, 2022 bear, flash crash, rate shock scenarios |

---

## Bubble Risk Score & Covered Call Strategy

<details>
<summary><strong>Bubble Risk Score</strong> — Real-time composite market risk indicator</summary>

Integrated from [Market-Bubble-Index-Dashboard](https://github.com/YichengYang-Ethan/Market-Bubble-Index-Dashboard).

**Components:**
- **SMA-200 Deviation** (0-40 pts) — How far the market has stretched above its 200-day moving average
- **Trend Acceleration** (0-30 pts) — Polynomial-fit measure of parabolic price acceleration
- **Volatility Regime** (0-30 pts) — Annualized realized volatility assessment

| Score | Regime | Action |
|-------|--------|--------|
| 0-39 | Low Risk | Hold shares, no CC |
| 40-54 | Moderate | Monitor |
| 55-65 | Elevated | Prepare CC orders |
| 66-100 | High Risk | Sell covered calls |

```python
from clawdfolio.analysis.bubble import fetch_bubble_risk

risk = fetch_bubble_risk()
print(f"Risk Score: {risk.drawdown_risk_score:.1f} ({risk.regime})")
print(f"Should sell CC: {risk.should_sell_cc}")
```

</details>

<details>
<summary><strong>Risk-Driven Covered Call Strategy</strong> — 83% win rate, +3.0% alpha (11-year backtest)</summary>

Uses Bubble Risk Score to determine **when** to sell calls and at **what delta**. Designed for long-term holders of leveraged ETFs (TQQQ) or broad-market ETFs (QQQ/SPY).

**Backtested Results (2014-2026, 64 parameter combinations):**

| Metric | Value |
|--------|-------|
| Optimal threshold | Risk Score >= 66 (P85 historical) |
| Optimal delta | 0.25 |
| Win rate | **83%** |
| Annualized alpha | **+3.0%** over buy-and-hold |
| Assignment rate | 1.5% (1 in 11 years) |

```python
from clawdfolio.strategies.covered_call import CoveredCallStrategy, get_cc_recommendation

strategy = CoveredCallStrategy(tickers=["TQQQ"])
signals = strategy.check_signals()

for sig in signals:
    print(f"{sig.ticker}: {sig.action.value} δ={sig.target_delta} "
          f"Risk={sig.bubble_risk_score:.0f} ({sig.regime})")

# Quick one-liner:
print(get_cc_recommendation("TQQQ"))
```

Strategy methodology: [Options Strategy Playbook v2.1](docs/OPTIONS_STRATEGY_PLAYBOOK_v2.1.md)

</details>

---

## Configuration

### Environment Variables

```bash
# Longport
export LONGPORT_APP_KEY=your_app_key
export LONGPORT_APP_SECRET=your_app_secret
export LONGPORT_ACCESS_TOKEN=your_access_token

# Moomoo: Run OpenD locally on port 11111
```

### Config File (optional)

Place at `~/.config/clawdfolio/config.yaml` or pass via `--config`:

```yaml
brokers:
  longport:
    enabled: true
  futu:
    enabled: true
    extra:
      host: "127.0.0.1"
      port: 11111

alerts:
  pnl_trigger: 500.0
  rsi_high: 80
  rsi_low: 20

notifications:
  enabled: true
  gateway_url: "http://localhost:18789"
  telegram:
    bot_token: "your_token"
    chat_id: "your_chat_id"

rebalancing:
  tolerance: 0.03
  targets:
    - ticker: QQQ
      weight: 0.30
    - ticker: SPY
      weight: 0.25
    - ticker: NVDA
      weight: 0.15

option_buyback:
  enabled: true
  symbol: "TQQQ"
  targets:
    - name: "cc-june"
      strike: 60
      expiry: "2026-06-18"
      type: "C"
      trigger_price: 1.60
      qty: 2
      reset_pct: 0.20
```

### Supported Brokers

| Broker | Region | Status |
|--------|--------|--------|
| Demo | Global | Built-in |
| Longport | US/HK/SG | `pip install clawdfolio[longport]` |
| Moomoo/Futu | US/HK/SG | `pip install clawdfolio[futu]` |

---

## Finance Workflows

20 production workflows migrated from live trading infrastructure:

| Category | Examples |
|----------|---------|
| **Portfolio Reports** | Account report, portfolio analysis, risk breakdown |
| **Briefing Cards** | Daily brief (console + Telegram), multi-format |
| **Alerts & Monitors** | Price/RSI alerts, option buyback trigger |
| **Market Intelligence** | Real-time quotes, earnings calendar, market news |
| **Broker Snapshots** | Longport / Moomoo asset summaries |
| **Strategy** | DCA proposals, rebalancing |

```bash
clawdfolio finance list                # Browse all workflows
clawdfolio finance init                # Bootstrap workspace
clawdfolio finance run <workflow_id>   # Execute a workflow
```

---

<details>
<summary><strong>Changelog</strong></summary>

### v2.5.0 (2026-03-01)

- **Broker auto-discovery** — `get_broker("demo")` works from Python API without manual imports
- **History commands** — `history snapshot`, `history show`, `history performance` for NAV tracking
- **Rebalance commands** — `rebalance check` and `rebalance propose --amount` for target allocation
- **Dashboard command** — `clawdfolio dashboard` launches Streamlit UI
- **RebalancingConfig** — New `rebalancing.targets` and `rebalancing.tolerance` in config
- **NotificationConfig** — Added `enabled`, `gateway_url`, `timeout` fields
- **CLI argument position fix** — `--broker`, `--output`, `--config` work before or after subcommand
- **ConsoleFormatter** — Rich-formatted `print_history`, `print_performance`, `print_rebalance`

### v2.4.0 (2026-02-28)

- **Bubble Risk Score** — Real-time drawdown risk scoring (0-100) integrated from Market-Bubble-Index-Dashboard
- **Risk-driven Covered Call strategy** — Quantitative CC signals: 83% win rate, +3.0% alpha (11-year backtest)
- `CoveredCallStrategy`, `check_cc_signals()`, `get_cc_recommendation()` convenience API
- `fetch_bubble_risk()` with Dashboard API + live-calc fallback

### v2.3.0 (2026-02-16)

- Sortino ratio and CVaR/Expected Shortfall risk metrics
- Portfolio RSI in `analyze_risk()` output
- `clawdfolio export` CLI command (CSV/JSON)
- Dynamic US trading calendar with algorithmic holiday generation
- Coverage enforcement at 48%, Python 3.13 in CI, `pip-audit` scanning

### v2.2.0 (2026-02-14)

- Thread-safe market data caching
- Batch quote fetching via `yf.download` with per-ticker fallback
- PEP 561 compliance (`py.typed` marker)
- Config path migration to `clawdfolio` namespace (backward-compatible)

### v2.1.0 (2026-01-28)

- Options Strategy Playbook v2.1
- Research-to-execution framework for CC and Sell Put lifecycle

### v2.0.0 (2026-01-15)

- Full finance migration: 20 production workflows
- `clawdfolio finance` command group (list, init, run)
- Options quote/chain/buyback monitor

See [CHANGELOG.md](CHANGELOG.md) for full details.

</details>

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Run tests (`pytest tests/ -v`) and lint (`ruff check src/ tests/`)
4. Submit a Pull Request

```bash
pip install -e ".[dev]"    # Install with dev dependencies
pytest tests/ -v           # Run tests
ruff check src/ tests/     # Lint
```

## License

MIT License — see [LICENSE](LICENSE)

## Links

- [PyPI Package](https://pypi.org/project/clawdfolio/)
- [GitHub Repository](https://github.com/YichengYang-Ethan/clawdfolio)
- [Report Issues](https://github.com/YichengYang-Ethan/clawdfolio/issues)
- [Options Strategy Playbook](docs/OPTIONS_STRATEGY_PLAYBOOK_v2.1.md)
