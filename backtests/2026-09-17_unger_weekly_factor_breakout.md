# Backtest Report: Unger Weekly Factor Pattern Breakout

**Strategy file:** `strategies/2026-09-17_unger_weekly_factor_breakout.py`
**Hypothesis id:** 2026-09-17-171

## Source

TASC (Technical Analysis of Stocks & Commodities) September 2023 Traders'
Tips (implementing the August 2023 article), Andrea Unger, "The Weekly
Factor Pattern", via
https://traders.com/Documentation/FEEDbk_docs/2023/09/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl).

Original construction uses intraday SESSION functions (multi-session-per-day
futures). Adapted to this repo's daily-bar-only data (1 session = 1 day):
5-day compression filter (`|Open[5 days ago] - Close[yesterday]| <
RangeFilter * 5-day High-Low range`) gates a breakout entry (close breaks
above yesterday's high). Distinct compression-proxy mechanism from NR7
(narrowest-bar-range) and Bollinger/Keltner squeeze (band-width
percentile) -- first Weekly Factor Pattern strategy in this repo.

## Trading rule

`close > prior_high` breakout, gated by the WeeklyFactor compression
condition; exit on close falling below entry-bar's prior low, or a
`max_hold_days` time-stop. Long-only (source's short leg dropped per
SAFETY.md).

## Step 6 grid summary (range_filter x max_hold_days, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-2026)

- 108 cells total, **pass_fraction 0.250** (27/108)
- by_asset_class: equity 27/54 (0.500), crypto 0/54 (0.0, decisive)
- by_vol_regime: low 18/36 (0.500), mid 9/36 (0.25), high 0/36 (0.0)
- best_cell: QQQ, range_filter=0.75/max_hold=10, low-vol, Sharpe 2.56

## Single-config validators (per-symbol tuned)

| Symbol | Config | Trades | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|---|
| QQQ | range_filter=0.5/max_hold=10/window=5 | 157 | **1.257** PASS | **0.197** PASS | **1.041** PASS | **4/4 (1.0)** PASS | **0.144** PASS |
| SPY | range_filter=0.5/max_hold=15/window=10 | 121 | **1.178** PASS | **0.144** PASS | **0.982** PASS | **4/4 (1.0)** PASS | **0.063** PASS |

Crypto (BTC/USDT, ETH/USDT): grid found 0/54 passing cells -- decisive
rejection, no further local search run.

## Decision

**Accept (QQQ, SPY, per-symbol tuned); reject (BTC/USDT, ETH/USDT, decisive).**
