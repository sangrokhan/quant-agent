# ZigZag Higher-High/Higher-Low Trend-Continuation — Backtest Report

**Date:** 2026-09-07/08 (3rd iteration this cron trigger)
**Strategy file:** `strategies/2026-09-07_zigzag_hh_hl_trend_continuation.py`
**Source:** https://www.thinkmarkets.com/en/trading-academy/indicators-and-patterns/zigzag-indicator/

## Hypothesis

ZigZag pivots (confirmed swing highs/lows filtered by a minimum
percentage-deviation threshold) reveal Dow-theory market structure. Per
the source: "The ZigZag reveals a clear market structure by showing
higher highs and higher lows in uptrends... pivot points act as breakout
zones in trend continuations" and can double as a structural stop-loss
level ("set stop-loss below swing lows for long trades"). This strategy
enters long when a newly-confirmed ZigZag pivot high exceeds the prior
pivot high AND the most recent pivot low exceeds the pivot low before it
(HH+HL uptrend confirmation), exits below the last confirmed swing low or
after max_hold_days. First ZigZag-indicator strategy in this repo.

## Grid test (Step 6)

`param_grid`: deviation_pct∈{3.0,5.0,8.0}, max_hold_days∈{15,30}; symbols:
equity {QQQ,SPY}, crypto {BTC/USDT,ETH/USDT}; vol_regime_splits=3; period
2018-01-01..2026-09-01.

- **pass_fraction: 0.125** (9/72 cells)
- by_asset_class: equity 9/36, **crypto 0/36**
- by_vol_regime: low 7/24, mid 1/24, high 1/24 — edge concentrated in low-vol
- best_cell: QQQ, deviation_pct=3.0, max_hold_days=30, low-vol regime,
  Sharpe 2.94
- worst_cell: QQQ, deviation_pct=8.0, max_hold_days=30, high-vol regime,
  Sharpe -0.58

## Single-config validation (Step 7): QQQ, deviation_pct=3.0, max_hold_days=30

Full period 2018-01-01..2026-09-01:

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.837 | ≥1.0 | **FAIL (near-miss)** |
| Max drawdown | 21.2% | ≤25% | pass |
| Transaction-cost survival (86 trades, 10bps) | net Sharpe 0.734 | ≥0.5 | pass |
| Walk-forward (manual 4-split) | 1.00 (4/4 splits positive) | ≥0.75 | pass |
| Parameter sensitivity (6-point deviation_pct sweep 2-8%) | rel std 0.715 | ≤0.5 | **FAIL** |

## Decision: **REJECT**

Full-sample Sharpe on QQQ is a near-miss (0.837 vs 1.0), and the strategy
is highly brittle to the deviation_pct threshold choice: Sharpe drops from
0.84 at 3% to ~0.24-0.25 at 4-6% and to 0.056 at 8% — a cliff-edge rather
than a stable edge, confirmed by the parameter-sensitivity relative std of
0.715 (nearly 1.5x the 0.5 ceiling). Walk-forward and cost-survival both
pass comfortably, and QQQ low-vol grid cells look excellent (Sharpe up to
2.94), but the extreme sensitivity to the ZigZag deviation threshold and
the categorical crypto failure (0/36) make this too fragile to accept as
specified. Kept as a record; a future loop could try shrinking the grid
around 2-3% deviation only, or gating on a longer-term trend filter to
reduce the threshold-sensitivity.
