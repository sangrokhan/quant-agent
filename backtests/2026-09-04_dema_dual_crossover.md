# DEMA (Double Exponential MA) Dual Crossover — Backtest Report

**Hypothesis:** DEMA (Patrick Mulloy) = 2*EMA(n) - EMA(EMA(n)), designed to
reduce lag vs a plain EMA. Standard dual-DEMA crossover: fast DEMA crossing
above slow DEMA signals a long entry, opposite cross exits.

Source: Google search snippets (TradingView, LuxAlgo, TrendSpider,
Stockpathshala, PyQuantLab/Medium) corroborating the same DEMA formula and
standard crossover rule (web_search failed repeatedly with a DDGS/Yahoo TLS
connection error, fell back to browser_exec; QuantifiedStrategies.com's own
DEMA article 404'd, confirmed genuine 404 not a load failure).

## Step 6 — Grid test (fast_span x slow_span x asset class x vol regime)

Grid: `fast_span` in [10, 20], `slow_span` in [30, 50, 100], symbols
equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3.
72 cells total.

- **pass_fraction: 0.236 (17/72)**
- by_asset_class: equity 17/36 passed; **crypto 0/36 passed** (decisive reject)
- by_vol_regime: low 12/24; mid 4/24; high 1/24
- best_cell: QQQ, fast_span=10, slow_span=100, vol_regime=low, Sharpe 3.36

## Full-sample Sharpe by config (QQQ, SPY)

| fast_span | slow_span | QQQ Sharpe (trades, MDD) | SPY Sharpe (trades) |
|---|---|---|---|
| 10 | 30 | 0.858 (63) | 0.976 (77) |
| 10 | 50 | 0.992 (52) | 1.049 (52) |
| 10 | 100 | 1.357 (30, MDD 0.262 fail) | 0.906 (42) |
| 20 | 30 | 0.978 (48) | 0.761 (49) |
| **20** | **50** | 1.294 (31, MDD 0.296 fail) | 0.789 (36) |
| **20** | **100** | **1.203 (21, MDD 0.242 pass)** | 0.742 (27) |

The highest full-sample Sharpe configs (QQQ 10/100 and 20/50) both FAIL
max drawdown (0.262 and 0.296 respectively, over the 0.25 threshold) --
only fast=20/slow=100 clears both Sharpe AND max drawdown simultaneously.

## Step 7 — Single-config validation (QQQ, fast_span=20, slow_span=100)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.203 | 1.0 |
| Max drawdown | ✅ | 0.242 | 0.25 |
| Transaction cost survival (10bps/trade, 21 trades) | ✅ | 1.178 (net Sharpe) | 0.5 |
| Walk-forward (4 splits, manual date-slice; vectorbt splitter API bug as noted in prior entries) | ✅ | 1.0 (4/4 splits positive: 1.56, 0.06, 1.54, 1.66) | 0.75 |
| Parameter sensitivity (6-combo QQQ grid, rel. std) | ✅ | 0.163 | 0.5 |

**QQQ: all 5 validators pass, including a perfect 4/4 walk-forward split.**
Only 21 round-trip trades over 7.7yr, consistent with the slower slow_span=100
smoothing.

### SPY (same config)

Sharpe 0.742 -- a clear (not near-miss) rejection at this shared config;
SPY's own best config (fast=10/slow=50, Sharpe 1.049) is untested for the
other 4 validators since it's not the shared/primary config kept for QQQ.

## Outcome

**Accepted for QQQ only** (fast_span=20, slow_span=100). SPY rejected at
the shared config (Sharpe 0.742, not merely a coin-flip miss). Crypto
rejected decisively (0/36 grid cells).
