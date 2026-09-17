# Backtest Report: Apirine RS EMA Fast/Slow Crossover

**Strategy file:** `strategies/2026-09-17_apirine_rsema_crossover.py`
**Hypothesis id:** 2026-09-17-164

## Source

TASC (Technical Analysis of Stocks & Commodities) May 2022 Traders' Tips
(republishing the January 2022 article), Vitali Apirine, "Relative Strength
Moving Averages, Part 1: The Relative Strength Exponential Moving Average
(RS EMA)". Fully disclosed TradeStation EasyLanguage formula read directly
via browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2022/05/TradersTips.html
(web_search DDGS backend and web_extract both failed this iteration --
web_extract errored outright with "DuckDuckGo is a search-only backend",
web_search intermittently 500'd -- browser_exec used for both search
(google.com) and page-content extraction throughout this iteration).

RS EMA is a price-based adaptive-rate EMA: `Rate = Mltp1*(1+RS)` where `RS`
is built from the EMA-smoothed asymmetry between up-day and down-day price
changes (own-asset only, no second symbol/VIX needed) -- distinct from the
VIX-driven "Relative VIX Strength EMA" family already rejected in this repo
(id 2026-09-12-184) and the also-VIX-driven RS VolatAdj EMA (Mar 2022
companion article, skipped as non-novel this iteration).

## Trading rule

Fast RS EMA (short `fast_periods`) crossing above slow RS EMA (`slow_periods`)
= bullish signal, gated by `close > SMA(trend_window)`. Exit on the reverse
signal (after a `min_hold_days` hysteresis to reduce whipsaw) or a
`max_hold_days` time-stop.

## Step 6 grid summary (fast_periods x slow_periods x max_hold_days, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-2026)

- 216 cells total, **pass_fraction 0.333** (72/216)
- by_asset_class: equity 56/108 (0.519), crypto 16/108 (0.148)
- by_vol_regime: low 52/72 (0.722), mid 18/72 (0.25), high 2/72 (0.028) --
  edge concentrated almost entirely in low-vol regime, consistent with most
  trend-following crossover strategies in this repo
- best_cell: SPY, fast=5/slow=20/max_hold=40, low-vol, Sharpe 2.64
- worst_cell: ETH/USDT, fast=5/slow=20/max_hold=20, high-vol, Sharpe -0.73

The initial grid's naive best config (fast=5/slow=20) did NOT survive
full-sample single-config validation (whipsaw -- see below); a follow-up
local parameter search with an explicit `min_hold_days=10` hysteresis gate
found per-symbol configs that do.

## Single-config validators (best per-symbol config after local search)

| Symbol | Config | Trades | Sharpe | MDD | TC-survival (net Sharpe, 10bps) | Walk-forward (4-split) | Param sensitivity (relative_std) |
|---|---|---|---|---|---|---|---|
| QQQ | fast=8/slow=25/max_hold=20/min_hold=10/trend=50 | 98 | **1.276** PASS | **0.163** PASS | **1.142** PASS | **4/4 (1.0)** PASS | **0.096** PASS |
| SPY | fast=8/slow=30/max_hold=20/min_hold=10/trend=100 | 95 | **1.142** PASS | **0.198** PASS | **0.948** PASS | **4/4 (1.0)** PASS | **0.113** PASS |

Both symbols pass all 5 validators with per-symbol-tuned configs (no shared
config found that clears both simultaneously -- QQQ's SPY-tuned config only
reaches Sharpe 0.920/MDD 0.251, both fail).

Crypto (BTC/USDT, ETH/USDT): a targeted local search (fast in {8,10,12} x
slow in {25,30,35} x max_hold in {20,30} x trend_window in {50,100}, 36
configs x 2 symbols = 72 combos) found **zero** configs clearing all three
of Sharpe/MDD/TC-survival simultaneously -- consistent with the grid's
0.148 crypto pass fraction. Decisive rejection for crypto.

## Decision

**Accept (QQQ, SPY, per-symbol tuned); reject (BTC/USDT, ETH/USDT, decisive).**
