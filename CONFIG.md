# Clawdfolio Configuration Reference

## Config File Search Order

1. `--config` CLI argument
2. `CLAWDFOLIO_CONFIG` env var
3. `./config.yaml` (current directory)
4. `~/.config/clawdfolio/config.yaml`

Supports YAML and JSON formats.

## Full Configuration Example

```yaml
brokers:
  longport:
    enabled: true
    timeout: 30
  futu:
    enabled: true
    extra:
      host: "127.0.0.1"
      port: 11111

alerts:
  pnl_trigger: 500        # Absolute dollar P&L trigger
  pnl_step: 500           # Step size for P&L dedup
  rsi_high: 80            # RSI overbought threshold
  rsi_low: 20             # RSI oversold threshold
  single_stock_threshold_top10: 0.05   # 5% move for top-10 holdings
  single_stock_threshold_other: 0.10   # 10% move for other holdings
  move_step: 0.01         # 1% step for move dedup
  concentration_threshold: 0.25

# Leveraged ETF auto-scaling (threshold * leverage factor)
leveraged_etfs:
  TQQQ: ["QQQ", 3, "Nasdaq 100"]
  SOXL: ["SOXX", 3, "Semiconductors"]
  SQQQ: ["QQQ", -3, "Nasdaq 100"]
  UPRO: ["SPY", 3, "S&P 500"]

option_buyback:
  enabled: true
  symbol: TQQQ
  targets:
    - name: tqqq_mar_80c
      strike: 80.0
      expiry: "2026-03-21"
      option_type: C
      trigger_price: 0.15
      qty: 5
      reset_pct: 0.20

currency: USD
timezone: America/New_York
cache_ttl: 300           # Market data cache in seconds
output_format: console   # console | json
verbose: false
```

## Environment Variables

### Longport Broker
```bash
LONGPORT_APP_KEY=your_app_key
LONGPORT_APP_SECRET=your_app_secret
LONGPORT_ACCESS_TOKEN=your_access_token
LONGPORT_REGION=us                       # optional, defaults to "us"
```

### Moomoo/Futu Broker
No env vars needed. Requires moomoo OpenD running locally (default `127.0.0.1:11111`). Configure host/port in `brokers.futu.extra`.

### Config Override
```bash
CLAWDFOLIO_CONFIG=/path/to/config.yaml
```

## Broker Support

| Broker | Package | Auth | Notes |
|---|---|---|---|
| **Longport** | `clawdfolio[longport]` | Env vars | US equities, fd-level noise suppression for Rust SDK |
| **Moomoo/Futu** | `clawdfolio[futu]` | Local OpenD | US equities, TCP to `127.0.0.1:11111` |
| **Demo** | Built-in | None | 10 hardcoded positions, +/-2% random variance |
| **Aggregator** | Built-in | Per-broker | Merges multiple brokers, deduplicates positions |

## Monitors

### Price Monitor
Step-based deduplication: fires once per threshold crossing, then only on new steps. Leveraged ETFs auto-scale thresholds by leverage factor. State persisted to `~/.cache/clawdfolio/price_alert_state.json`.

### Earnings Monitor
Alerts for upcoming earnings within configurable window. Severity escalates when earnings are within 1 day or position weight >= 10%.

### Options Buyback Monitor
Stateful trigger monitor with file locking. Auto-resets when price rises above `trigger_price * (1 + reset_pct)`. State persisted to `~/.cache/clawdfolio/option_buyback_state.json`.
