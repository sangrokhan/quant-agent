# Chandelier Exit + StochRSI Dip-Buy — Backtest Report

**Hypothesis** (kb id 2026-09-04-035): a Chandelier Exit(22, ATR mult 3)
trailing-stop defines an established uptrend (close > chandelier long-stop
line); StochRSI dipping below 0.20 then recovering above it times a
dip-buy entry within that uptrend. Exit when close crosses below the
Chandelier trailing-stop line.

**Source**: StockCharts ChartSchool Chandelier Exit article
(https://chartschool.stockcharts.com/.../chandelier-exit), fetched via
browser_exec after web_extract failed with the recurring DDGS
search-only-backend error (web_search succeeded first try for this
keyword). Distinct from the prior chandelier-exit strategy in this repo
(2026-09-04-025, all-time-high breakout entry) — this uses a pullback
dip-buy entry mechanism.

## Grid test (Step 6)

`param_grid = {atr_multiplier: [2.5,3.0], oversold_threshold: [0.15,0.20], chandelier_window: [22]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3,
2019-01-01 to 2026-09-01. 48 total cells.

- pass_fraction: **0.229** (11/48)
- by_asset_class: equity 11/24, crypto 0/24
- by_vol_regime: low 8/16, mid 3/16, high 0/16
- best_cell: SPY, atr_multiplier=3.0, oversold_threshold=0.20, low-vol tercile, Sharpe 1.939 (not representative of full sample, see below)

## Full-sample validators (Step 7) — grid-best config (atr_multiplier=3.0, oversold_threshold=0.20, chandelier_window=22)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Trades |
|---|---|---|---|---|
| QQQ | 0.420 (fail, thr 1.0) | 0.336 (fail, thr 0.25) | 0.358 (fail, thr 0.5) | 46 |
| SPY | 0.455 (fail, thr 1.0) | 0.253 (fail, thr 0.25) | 0.377 (fail, thr 0.5) | 44 |

Walk-forward (SPY, 4 manual date-slices): 2/4 splits positive = 0.5 pass
fraction, fails the 0.75 threshold. Parameter sensitivity (atr_multiplier
in {2.5,3.0,3.5}, SPY): relative std 0.333, passes the 0.5 ceiling but this
is moot given the decisive Sharpe/MDD failures.

## Decision: REJECTED (all asset classes)

Both QQQ and SPY fail Sharpe, max drawdown, and transaction-cost survival
decisively at the grid-optimal config — the grid's apparently strong
low-vol-tercile cell (Sharpe 1.94 on SPY) did not generalize to the full
sample (0.455). This is a clearer, less-ambiguous rejection than the
similarly-styled Ichimoku attempt (2026-09-04-034, near-miss) despite a
similar overall grid pass_fraction (0.229 vs 0.25) and identical
low-vol-tercile concentration pattern — illustrating that pass_fraction and
vol-regime concentration alone are not sufficient signals of quality; the
full-sample single-config check remains essential. Crypto rejected
decisively (0/24 grid cells).
