# Backtest Report: Points & Line Chart Trend-Flip

**Strategy file:** `strategies/2026-09-18_points_and_line_chart_trend_flip.py`
**Hypothesis id:** 2026-09-18-002
**Source:** https://traders.com/Documentation/FEEDbk_docs/2025/11/TradersTips.html (TASC Nov 2025, Mohamed Ashraf & Mohamed Meregy, "The Points & Line Chart", fully disclosed EasyLanguage)

## Hypothesis

TASC's Points & Line (P&L) chart floors price to a discrete Point-and-Figure-style
box size (lookup table keyed to the symbol's own price level), placing a new line
vertex only when price advances >=1 box in the current direction or reverses
>= ReversalAmount (default 3) boxes against it. This iteration reconstructs the
source's own `Dir` state machine (its internal +1/-1 direction flag) as a trend
signal: long entry when Dir flips from -1 to +1 (a confirmed new up-leg begins),
exit when Dir flips back to -1 or a max_hold_days time-stop, gated by an
SMA(trend_window) uptrend filter. First strategy in this repo based on this
discrete price-level-keyed box quantization (distinct from fixed-ATR/percentage
Renko, Kagi, Three-Line-Break, and Point-and-Figure double-top-breakout, all
already tested).

## Grid Test Summary (Step 6)

Grid: `reversal_amount` in {2,3,4}, `trend_window` in {50,100}, `max_hold_days` in
{40,60}, symbols equity {QQQ, SPY} + crypto {BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- total_cells: 144, passed_cells: 33, **pass_fraction: 0.229**
- by_asset_class: equity 24/72, crypto 9/72 (edge concentrated in equity)
- by_vol_regime: low 24/48, mid 6/48, high 3/48 (edge concentrated in low-vol regime)
- best_cell: ETH/USDT mid-vol, reversal_amount=3/trend_window=100/max_hold_days=40, Sharpe 2.19 (isolated slice, not representative of full-sample crypto performance -- see below)
- worst_cell: ETH/USDT high-vol, reversal_amount=2/trend_window=100/max_hold_days=40, Sharpe -1.05

A follow-up full-sample sweep (widening trend_window to {150,200}, max_hold_days
to {90}) found QQQ full-sample Sharpe/MDD passing at
`reversal_amount=3, trend_window=200, max_hold_days=90`; the identical config did
not rescue SPY (best full-sample Sharpe found ~0.86, still below the 1.0 threshold
across a wide trend_window/max_hold_days re-sweep).

## Single-Config Validation (Step 7)

Config: `reversal_amount=3, trend_window=200, max_hold_days=90`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward (4-slice) | Param sensitivity (rel std, sweep reversal_amount 2/3/4) | Verdict |
|--------|--------|-----|------------------------|------------------------|-----------------------------------------------------------|---------|
| QQQ    | 1.123  | 0.128 | 1.090                 | 0.75 (3/4 slices positive) | 0.184                                                  | **ACCEPT** |

SPY: best full-sample config found only reaches Sharpe ~0.86, below the 1.0 threshold
across a broad re-sweep -- rejected (not a near-miss worth further chasing this
iteration).

Crypto (BTC/USDT, ETH/USDT): the grid's edge was concentrated in isolated mid-vol
slices (not full-sample), consistent with this repo's frequent finding that box/
brick-based chart constructions don't transfer cleanly to crypto's different bar
granularity/volatility profile — not pursued further this iteration; left as a
future per-symbol retune candidate if revisited.

## Decision (Step 8)

**Accepted for QQQ only** (equity), all 5 validators pass. SPY and both crypto
symbols rejected this iteration.
