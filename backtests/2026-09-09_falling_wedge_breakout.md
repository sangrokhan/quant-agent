# Falling Wedge Breakout — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_falling_wedge_breakout.py`
**Outcome:** REJECTED (decisive, weak grid pass_fraction)

## Hypothesis

Per Dukascopy Bank SA's Falling Wedge Pattern guide (Google search
result, query "rising wedge falling wedge chart pattern trading strategy
exact entry exit rules"): a falling wedge is two downward-sloping,
converging trendlines connecting a sequence of lower highs and lower
lows, with highs falling faster than lows (narrowing range), signaling
waning downward momentum. Source's exact rule: enter long on a breakout
above the upper (descending-highs) trendline; stop below the lower
trendline; target = wedge height projected up from breakout.

Approximated systematically via rolling linear regression on trailing
highs/lows: a falling wedge is confirmed when both trendline slopes are
negative, the high-line slope is more negative than the low-line slope
(converging), and the current width has narrowed below `narrow_ratio`
of the window-start width. Entry on close breaking the projected upper
trendline value; exit on profit target, stop-loss at the lower
trendline, or a max_hold_days time-stop.

First Wedge-pattern (converging trendline) strategy in this repo (0
prior hits) — distinct from Darvas Box (frozen box, no slope) and
TTM Squeeze/Bollinger Bandwidth (volatility-band width, not two
independently-sloped price trendlines).

## Grid summary (window=[15,20,30] x narrow_ratio=[0.6,0.7,0.8] x
max_hold_days=[20], equity=[QQQ,SPY] x crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 108, passed_cells: 5, pass_fraction: **0.046**
- by_asset_class: equity 5/54 (0.093), crypto 0/54 (0.0 — decisive fail)
- by_vol_regime: low 0/36 (0.0), mid 3/36 (0.083), high 2/36 (0.056)
- best_cell: window=15/narrow_ratio=0.8/max_hold_days=20, SPY high-vol
  regime, Sharpe 1.50
- worst_cell: window=20/narrow_ratio=0.6/max_hold_days=20, QQQ low-vol
  regime, Sharpe -1.24

## Verdict: REJECTED (decisive)

Grid pass_fraction of 0.046 is among the weakest results tested in this
repo — the falling-wedge pattern, as approximated by rolling-OLS
trendline slopes on highs/lows, essentially does not produce a tradeable
edge on daily bars. Unlike most of this repo's decisive rejections
(which fail primarily on Sharpe with reasonable trade counts), this
pattern is compounded by construction fragility: the rolling-slope
approximation of a "wedge" is a fairly loose proxy for the visual pattern
traders actually identify (which typically also requires the two
trendlines to have started from a genuine local high/swing point, not
just any 15-30 bar rolling window), so the resulting signal is likely
noisy/non-selective. No single-config validator suite run given the
grid's decisive weakness — not worth the additional compute per Step 7's
guidance to skip full validation on a clearly-failing grid.

**Note for future loops:** if revisiting chart-pattern-family strategies
(triangles, flags, head-and-shoulders), a proper swing-pivot-based
construction (anchoring trendlines to confirmed local extrema via
`scipy.signal.argrelextrema` or similar, rather than a fixed rolling
window) would likely be a more faithful backtest of the visual pattern
and worth trying before writing off geometric chart patterns entirely.
