# Clawdfolio 🦙📊

[![CI](https://github.com/YichengYang-Ethan/clawdfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/YichengYang-Ethan/clawdfolio/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/YichengYang-Ethan/clawdfolio/branch/main/graph/badge.svg)](https://codecov.io/gh/YichengYang-Ethan/clawdfolio)
[![PyPI](https://img.shields.io/pypi/v/clawdfolio.svg)](https://pypi.org/project/clawdfolio/)
[![Downloads](https://static.pepy.tech/badge/clawdfolio/month)](https://pepy.tech/project/clawdfolio)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[English](README.md) | 中文

> **生产级量化投资组合工具包** — 多券商聚合、机构级风险分析、组合再平衡、期权全生命周期管理，以及 20+ 自动化金融工作流。

---

## 为什么选择 Clawdfolio？

| 传统工具 | Clawdfolio |
|----------|------------|
| 手动录入数据 | 自动同步长桥、富途持仓 |
| 简单盈亏统计 | VaR、夏普比率、Beta、最大回撤、HHI |
| 单一券商视图 | 多券商聚合 |
| Excel 设置警报 | 智能 RSI / 价格 / 盈亏警报 |
| 无再平衡功能 | 目标配置跟踪 + 定投分配方案 |
| 无法扩展 | Python API + CLI + Streamlit 仪表盘 |

---

## 功能特性

### 核心持仓管理
- **多券商支持** — 长桥证券 (Longport)、富途牛牛 (Moomoo)、演示模式
- **持仓历史** — 快照追踪、净值曲线、各时段业绩指标
- **组合再平衡** — 目标配置偏离检测、DCA 感知的再平衡方案
- **智能警报** — 价格异动、RSI 超买超卖、盈亏阈值，支持通知推送

### 风险与分析
- **风险分析** — 波动率、Beta、夏普/索提诺比率、VaR/CVaR、最大回撤、GARCH 预测
- **集中度分析** — HHI 指数、行业暴露、相关性警告
- **压力测试** — 5 个历史场景（COVID 崩盘、2022 熊市等），支持杠杆 ETF 放大效应
- **技术指标** — RSI、SMA、EMA、布林带
- **Fama-French 因子** — 三因子暴露分析，含 Alpha 估计

### 期权与策略
- **期权工具集** — 实时 Greeks、期权链快照、回补触发监控
- **泡沫风险评分** — 复合市场风险指标（[Market-Bubble-Index-Dashboard](https://github.com/YichengYang-Ethan/Market-Bubble-Index-Dashboard)）
- **风险驱动 Covered Call** — 11 年回测验证：**83% 胜率**、**+3.0% 年化超额收益**

### 自动化
- **20+ 金融工作流** — 报告、警报、行情情报、券商快照
- **财报日历** — 追踪持仓股票财报日期
- **仪表盘** — 基于 Streamlit 的交互式仪表盘

---

## 快速开始

### 安装

```bash
pip install clawdfolio                  # 核心包（含演示券商）
pip install clawdfolio[longport]        # + 长桥券商
pip install clawdfolio[futu]            # + 富途券商
pip install clawdfolio[all]             # 全部安装
```

### 命令行

```bash
# 持仓
clawdfolio summary                     # 持仓概览
clawdfolio summary --broker demo       # 使用演示券商
clawdfolio risk --detailed             # 风险指标（含 RSI、行业、GARCH）

# 行情数据
clawdfolio quotes AAPL TSLA NVDA       # 实时行情
clawdfolio alerts                      # 查看警报
clawdfolio earnings                    # 财报日历

# 历史与再平衡
clawdfolio history snapshot            # 保存持仓快照
clawdfolio history show --days 30      # 查看净值历史
clawdfolio history performance         # 业绩指标
clawdfolio rebalance check             # 检查目标配置偏离
clawdfolio rebalance propose --amount 5000  # 定投分配方案

# 分析
clawdfolio dca AAPL --months 12        # 定投回测
clawdfolio stress                      # 压力测试
clawdfolio factors                     # Fama-French 因子暴露
clawdfolio bubble                      # 市场泡沫指数

# 期权
clawdfolio options expiries TQQQ
clawdfolio options quote TQQQ --expiry 2026-06-18 --strike 60 --type C
clawdfolio options chain TQQQ --expiry 2026-06-18

# 仪表盘
clawdfolio dashboard                   # 启动 Streamlit 仪表盘
```

**输出示例** (`clawdfolio summary --broker demo`)：

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

> `--broker`、`--output`、`--config` 等参数可以放在子命令之前或之后：
> `clawdfolio --broker demo summary` 与 `clawdfolio summary --broker demo` 等效。

### Python API

```python
from clawdfolio.brokers import get_broker
from clawdfolio.analysis import analyze_risk

broker = get_broker("demo")  # 或 "longport"、"futu"
broker.connect()

portfolio = broker.get_portfolio()
metrics = analyze_risk(portfolio)

print(f"净资产: ${portfolio.net_assets:,.2f}")
print(f"夏普比率: {metrics.sharpe_ratio:.2f}")
print(f"VaR 95%: {metrics.var_95:.2%}")
```

---

## 风险指标

| 指标 | 说明 |
|------|------|
| **波动率** | 20 日和 60 日年化波动率，GARCH(1,1) 预测 |
| **Beta** | 与 SPY/QQQ 基准的相关性 |
| **夏普比率** | 风险调整后收益 |
| **索提诺比率** | 仅计入下行波动的风险调整收益 |
| **VaR / CVaR** | 在险价值 (95%/99%) + 预期损失 |
| **最大回撤** | 最大峰值到谷值跌幅 |
| **HHI** | 投资组合集中度指数 |
| **压力测试** | COVID-19、2022 熊市、闪崩、加息冲击等场景 |

---

## 泡沫风险评分与 Covered Call 策略

<details>
<summary><strong>泡沫风险评分</strong> — 实时复合市场风险指标</summary>

集成自 [Market-Bubble-Index-Dashboard](https://github.com/YichengYang-Ethan/Market-Bubble-Index-Dashboard)。

**三大评分维度：**
- **SMA-200 偏离** (0-40 分) — 市场价格相对 200 日均线的偏离程度
- **趋势加速** (0-30 分) — 多项式拟合衡量抛物线式价格加速
- **波动率体制** (0-30 分) — 年化已实现波动率评估

| 评分 | 体制 | 操作建议 |
|------|------|----------|
| 0-39 | 低风险 | 持有股票，不卖 CC |
| 40-54 | 中等 | 监控观察 |
| 55-65 | 升高 | 准备 CC 订单 |
| 66-100 | 高风险 | 执行 Covered Call |

```python
from clawdfolio.analysis.bubble import fetch_bubble_risk

risk = fetch_bubble_risk()
print(f"风险评分: {risk.drawdown_risk_score:.1f} ({risk.regime})")
print(f"是否应卖 CC: {risk.should_sell_cc}")
```

</details>

<details>
<summary><strong>风险驱动 Covered Call 策略</strong> — 83% 胜率，+3.0% 超额收益（11 年回测）</summary>

基于泡沫风险评分，决定**何时**卖出看涨期权以及选择**什么** Delta。专为杠杆 ETF (TQQQ) 或宽基 ETF (QQQ/SPY) 长期持有者设计。

**回测结果 (2014-2026, 64 种参数组合)：**

| 指标 | 数值 |
|------|------|
| 最优阈值 | 风险评分 >= 66 (历史 P85) |
| 最优 Delta | 0.25 |
| 胜率 | **83%** |
| 年化超额收益 | **+3.0%** (相对买入并持有) |
| 被行权率 | 1.5% (11 年仅 1 次) |

```python
from clawdfolio.strategies.covered_call import CoveredCallStrategy, get_cc_recommendation

strategy = CoveredCallStrategy(tickers=["TQQQ"])
signals = strategy.check_signals()

for sig in signals:
    print(f"{sig.ticker}: {sig.action.value} δ={sig.target_delta} "
          f"风险={sig.bubble_risk_score:.0f} ({sig.regime})")

# 快速一行调用：
print(get_cc_recommendation("TQQQ"))
```

策略方法论详见：[期权策略手册 v2.1](docs/OPTIONS_STRATEGY_PLAYBOOK_v2.1.md)

</details>

---

## 配置

### 环境变量

```bash
# 长桥证券
export LONGPORT_APP_KEY=your_app_key
export LONGPORT_APP_SECRET=your_app_secret
export LONGPORT_ACCESS_TOKEN=your_access_token

# 富途：本地运行 OpenD，端口 11111
```

### 配置文件（可选）

放置于 `~/.config/clawdfolio/config.yaml`，或通过 `--config` 指定：

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

### 支持的券商

| 券商 | 地区 | 安装方式 |
|------|------|----------|
| 演示模式 | 全球 | 内置 |
| 长桥证券 | 美/港/新 | `pip install clawdfolio[longport]` |
| 富途牛牛 | 美/港/新 | `pip install clawdfolio[futu]` |

---

## 金融工作流

从实盘交易基础设施迁移的 20 个生产工作流：

| 类别 | 示例 |
|------|------|
| **持仓报告** | 账户报告、投组分析、风险拆解 |
| **简报卡片** | 每日简报（终端 + Telegram）、多格式 |
| **警报与监控** | 价格/RSI 警报、期权回补触发 |
| **市场情报** | 实时行情、财报日历、市场新闻 |
| **券商快照** | 长桥/富途资产摘要 |
| **策略** | 定投提案、再平衡 |

```bash
clawdfolio finance list                # 浏览所有工作流
clawdfolio finance init                # 初始化工作区
clawdfolio finance run <workflow_id>   # 执行工作流
```

---

<details>
<summary><strong>更新日志</strong></summary>

### v2.5.0 (2026-03-01)

- **券商自动发现** — `get_broker("demo")` 从 Python API 调用无需手动 import
- **历史命令** — `history snapshot`、`history show`、`history performance` 实现净值追踪
- **再平衡命令** — `rebalance check` 和 `rebalance propose --amount` 实现目标配置管理
- **仪表盘命令** — `clawdfolio dashboard` 启动 Streamlit 交互界面
- **再平衡配置** — 新增 `rebalancing.targets` 和 `rebalancing.tolerance` 配置项
- **通知配置** — NotificationConfig 新增 `enabled`、`gateway_url`、`timeout` 字段
- **CLI 参数位置修复** — `--broker`、`--output`、`--config` 可放在子命令前后任意位置
- **控制台格式化** — Rich 格式化的 `print_history`、`print_performance`、`print_rebalance`

### v2.4.0 (2026-02-28)

- **泡沫风险评分** — 集成 Market-Bubble-Index-Dashboard 的实时回撤风险评分 (0-100)
- **风险驱动 Covered Call 策略** — 量化 CC 信号：83% 胜率，+3.0% 超额收益（11 年回测）
- `CoveredCallStrategy`、`check_cc_signals()`、`get_cc_recommendation()` 便捷 API
- `fetch_bubble_risk()` 支持 Dashboard API + 本地计算回退

### v2.3.0 (2026-02-16)

- 索提诺比率和 CVaR/预期损失风险指标
- `analyze_risk()` 输出中新增 Portfolio RSI
- `clawdfolio export` CLI 命令（CSV/JSON）
- 动态美股交易日历（算法化节假日生成）
- 覆盖率提升至 48%，Python 3.13 CI 支持，`pip-audit` 扫描

### v2.2.0 (2026-02-14)

- 线程安全市场数据缓存
- 批量报价获取，支持逐个回退
- PEP 561 合规（`py.typed` 标记）
- 配置路径迁移至 `clawdfolio` 命名空间（向后兼容）

### v2.1.0 (2026-01-28)

- 期权策略手册 v2.1
- CC 与 Sell Put 全生命周期的研究到执行框架

### v2.0.0 (2026-01-15)

- 全量金融迁移：20 个生产工作流
- `clawdfolio finance` 命令组（list、init、run）
- 期权报价/期权链/回补监控

详见 [CHANGELOG.md](CHANGELOG.md)。

</details>

---

## 贡献

欢迎贡献代码！请按以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/my-feature`)
3. 运行测试 (`pytest tests/ -v`) 和检查 (`ruff check src/ tests/`)
4. 提交 Pull Request

```bash
pip install -e ".[dev]"    # 安装开发依赖
pytest tests/ -v           # 运行测试
ruff check src/ tests/     # 代码检查
```

## 许可证

MIT License — 查看 [LICENSE](LICENSE)

## 链接

- [PyPI 包](https://pypi.org/project/clawdfolio/)
- [GitHub 仓库](https://github.com/YichengYang-Ethan/clawdfolio)
- [问题反馈](https://github.com/YichengYang-Ethan/clawdfolio/issues)
- [期权策略手册](docs/OPTIONS_STRATEGY_PLAYBOOK_v2.1.md)
