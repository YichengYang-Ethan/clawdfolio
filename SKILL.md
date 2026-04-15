---
name: clawdfolio
description: "Quantitative portfolio toolkit — multi-broker aggregation (Longport, Moomoo/Futu), institutional risk analytics (Sharpe, Sortino, VaR, CVaR, Beta, RSI), options strategy lifecycle, 20+ finance workflows, and CSV/JSON export. Use when the user asks about portfolio analysis, risk metrics, stock quotes, DCA strategy, earnings, options, or financial data export."
license: MIT
allowed-tools: "Bash(clawdfolio *), Bash(pip install clawdfolio*), Bash(python -c *clawdfolio*), Bash(python -m clawdfolio*), Read, Glob, Grep, Edit, Write"
metadata:
  version: 2.3.0
  author: YICHENG YANG
  argument-hint: "<command> [options]"
  keywords:
    - quantitative-finance
    - portfolio-analytics
    - risk-management
    - options-trading
    - finance
    - dca
  dependencies:
    - pandas>=2.0.0
    - numpy>=1.24.0
    - yfinance>=0.2.30
    - pyyaml>=6.0
    - rich>=13.0.0
  optional_dependencies:
    longport:
      - longport>=1.0.0
    futu:
      - futu-api>=7.0.0
    all:
      - longport>=1.0.0
      - futu-api>=7.0.0
---

# Clawdfolio

Repo: https://github.com/YichengYang-Ethan/clawdfolio

---

## CLI Commands

All commands support `--broker {longport,futu,demo,all}`, `--output {console,json}`, and `--config PATH`.

### Portfolio

```bash
clawdfolio summary              # Portfolio overview (default command)
clawdfolio summary --top 20     # Show top 20 holdings
clawdfolio quotes AAPL MSFT     # Real-time quotes
clawdfolio alerts               # Price/RSI/PnL/concentration alerts
clawdfolio alerts --severity critical
```

### Risk Analysis

```bash
clawdfolio risk                 # Volatility, Beta, Sharpe, Sortino, VaR, CVaR, drawdown
clawdfolio risk --detailed      # + RSI extremes, concentration, sector exposure, portfolio RSI
```

### Earnings

```bash
clawdfolio earnings             # Upcoming earnings (default 14 days)
clawdfolio earnings --days 30   # 30-day lookahead
```

### DCA (Dollar-Cost Averaging)

```bash
clawdfolio dca                  # DCA signals for portfolio (rebalance + dip detection)
clawdfolio dca AAPL --months 12 --amount 1000   # Historical DCA backtest
```

Signal types: `REGULAR` (scheduled), `DIP` (price drop from recent high), `REBALANCE` (weight deviation from target).

### Export

```bash
clawdfolio export portfolio                  # CSV to stdout
clawdfolio export portfolio --format json    # JSON to stdout
clawdfolio export risk --file risk.csv       # Risk metrics to file
clawdfolio export alerts --format json --file alerts.json
```

Export targets: `portfolio`, `risk`, `alerts`. Formats: `csv`, `json`.

### Options

```bash
clawdfolio options expiries TQQQ
clawdfolio options chain TQQQ --expiry 2026-03-21 --side calls --limit 10
clawdfolio options quote TQQQ --expiry 2026-03-21 --strike 80 --type C
clawdfolio options buyback          # Check buyback triggers from config
clawdfolio options buyback --strict # Exit code 1 if no targets triggered
```

### Finance Workflows

20 bundled workflows across 7 categories. Validated setup sequence:

1. **Verify broker connectivity**: `clawdfolio summary --broker demo` (should show 10 demo positions)
2. **Init workspace**: `clawdfolio finance init` then verify with `ls ~/.clawdfolio/finance`
3. **List available workflows**: `clawdfolio finance list`
4. **Run a workflow**: `clawdfolio finance run portfolio_daily_brief_tg`
5. **Check output**: Add `--output json` if you need machine-readable results; on error, retry with `--broker demo` to isolate broker vs. workflow issues

```bash
clawdfolio finance list --category alerts_monitors  # Filter by category
clawdfolio finance run dca_proposal_tg -- --budget 5000  # Pass extra args
```

Categories: `portfolio_reports`, `briefing_cards`, `alerts_monitors`, `market_intel`, `broker_snapshots`, `strategy`, `security`.

Key workflows:
| ID | Description |
|---|---|
| `portfolio_report` | Daily portfolio report with performance, risk, holdings |
| `portfolio_daily_brief_tg` | Telegram-friendly daily brief card |
| `portfolio_alert_monitor` | Deduplicated RSI/PnL/concentration/move alerts |
| `option_buyback_monitor` | Stateful option buyback trigger monitor |
| `earnings_calendar` | Upcoming earnings for current holdings |
| `dca_proposal_tg` | Budget-constrained DCA proposal card |
| `account_report` | Combined Longport + moomoo snapshot |

Workspace: `~/.clawdfolio/finance` (configurable with `--workspace`).

---

## Configuration

Config file search order: `--config` flag > `CLAWDFOLIO_CONFIG` env var > `./config.yaml` > `~/.config/clawdfolio/config.yaml`. Supports YAML and JSON.

Brokers supported: Longport (env vars), Moomoo/Futu (local OpenD), Demo (built-in), Aggregator (multi-broker merge).

See [CONFIG.md](CONFIG.md) for full configuration reference, environment variables, broker setup, and monitor details.

---

## Python API

Key imports for programmatic use:

```python
from clawdfolio import Symbol, Position, Quote, Portfolio, RiskMetrics, Alert
from clawdfolio.brokers import get_broker
from clawdfolio.analysis.risk import analyze_risk
from clawdfolio.analysis.technical import calculate_rsi, calculate_macd
from clawdfolio.market import get_price, get_history, is_market_open
from clawdfolio.strategies.dca import DCAStrategy, calculate_dca_performance
from clawdfolio.output import export_portfolio_csv, export_risk_json
```

See [API.md](API.md) for full API reference with usage examples.
