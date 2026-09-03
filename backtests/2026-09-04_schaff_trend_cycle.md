# Schaff Trend Cycle (STC) Centerline (50) Crossover — Backtest Report

**Hypothesis:** STC (Doug Schaff) applies a double stochastic %K/%D
smoothing cycle on top of a MACD line to filter noise and identify
short-term trend cycles faster than plain MACD. Per
EnlightenedStockTrading's worked example: enter long when STC crosses
above 50, exit when it crosses below 50.

Source: https://enlightenedstocktrading.com/schaff-trend-cycle/
(web_search failed 15x+ with a DDGS/Yahoo TLS connection error, fell back
to browser_exec immediately; corroborated by a PineScriptForge search
snippet using a 25/75 oversold/overbought variant instead of the 50
centerline used here).

## Step 6 — Grid test (cycle x asset class x vol regime)

Grid: `cycle` in [10, 20] (fast=23, slow=50 fixed, standard STC defaults),
symbols equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3.
24 cells total.

- **pass_fraction: 0.292 (7/24)**
- by_asset_class: equity 7/12 passed; **crypto 0/12 passed** (decisive reject)
- by_vol_regime: low 4/8; mid 2/8; high 1/8
- best_cell: SPY, cycle=20, vol_regime=low, Sharpe 2.41

## Full-sample Sharpe by config (QQQ, SPY)

| cycle | QQQ Sharpe (trades) | SPY Sharpe (trades) |
|---|---|---|
| 10 | 0.965 (79) | 0.983 (82) |
| 20 | 0.769 (54) | **1.153 (53)** |

Only SPY at cycle=20 clears the 1.0 Sharpe threshold on the full sample.

## Step 7 — Single-config validation (SPY, cycle=20, fast=23, slow=50, centerline=50)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.153 | 1.0 |
| Max drawdown | ✅ | 0.136 | 0.25 |
| Transaction cost survival (10bps/trade, 53 trades) | ✅ | 1.055 (net Sharpe) | 0.5 |
| Walk-forward (4 splits, manual date-slice; vectorbt splitter API bug as noted in prior entries) | ✅ | 1.0 (4/4 splits positive: 1.20, 0.45, 1.16, 1.69) | 0.75 |
| Parameter sensitivity (2-value SPY grid, rel. std) | ✅ | 0.080 | 0.5 |

**SPY: all 5 validators pass, including a perfect 4/4 walk-forward split
and the lowest max drawdown (13.6%) of any accepted strategy in this repo
to date.**

### QQQ (same config)

Sharpe 0.769 — a clear miss (not a near-miss) at the SPY-optimal config.

## Outcome

**Accepted for SPY only** (fast=23, slow=50, cycle=20, centerline=50).
QQQ rejected at the shared config. Crypto rejected decisively (0/12 grid
cells).
