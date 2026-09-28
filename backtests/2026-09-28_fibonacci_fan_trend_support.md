# Fibonacci Fan Diagonal Trendline Breakout — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_fibonacci_fan_trend_support.py`
**Source:** https://www.investopedia.com/terms/f/fibonaccifan.asp (James Chen, Investopedia; read via browser_exec — web_extract's ddgs backend is search-only and cannot extract URL content)

## Hypothesis

A Fibonacci fan draws diagonal trendlines from a swing-low origin through
price points at the 23.6/38.2/50/61.8% Fibonacci retracement levels
(measured at the swing-high's time position), extrapolated forward in
time. Traders use these diagonal (time-varying) lines as dynamic
support/resistance. This is the first Fibonacci **Fan** strategy tested in
this repo — distinct from the already-tested Fibonacci **Retracement**
strategy (2026-09-03-022, static horizontal levels of one completed swing).

Tested rule: long entry when close crosses above the upper fan line
(ratio=0.5 or 0.618) while price is above its SMA(200) trend filter; exit
when close crosses below the lower fan line (ratio=0.382) or a
`max_hold_days` time-stop.

## Grid test summary (swing_lookback∈{40,60,90} × upper_ratio∈{0.5,0.618} × max_hold_days∈{15,25}, QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles)

- total_cells: 144, passed_cells: 25, **pass_fraction: 0.174**
- by_asset_class: equity 12/72 passed; crypto 13/72 passed
- by_vol_regime: low 13/48; mid 9/48; high 3/48 (edge decays sharply in high-vol regime — consistent with a support/resistance-reversal-style tool being unreliable once volatility breaks structure)
- best_cell: SPY, swing_lookback=40, upper_ratio=0.5, max_hold_days=15, low-vol regime, Sharpe 1.986
- worst_cell: QQQ, swing_lookback=60, upper_ratio=0.5, max_hold_days=15, mid-vol regime, Sharpe -1.635

## Single-config validation (best config: swing_lookback=40, upper_ratio=0.5, max_hold_days=15)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward (manual 4-split fallback*) | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| SPY | 0.872 (FAIL, thr 1.0) | 0.047 (PASS, thr 0.25) | 0.632 (PASS, thr 0.5) | 0.75 (PASS, thr 0.75) | 0.396 (PASS, thr 0.5) |
| QQQ | -0.352 (FAIL) | 0.141 (PASS) | -0.449 (FAIL) | 0.25 (FAIL) | 11.42 (FAIL) |

\* `check_walk_forward`'s `vbt.utils.splitting.RangeSplitter` raised
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` in
this repo's installed vectorbt version (known repo issue, see
`run_validate_2dance.py`) — used the established manual chronological
4-way split fallback instead.

## Decision: **REJECT**

Full-sample Sharpe on the best full-period-weighted config (0.872 SPY,
-0.352 QQQ) falls short of the 1.0 threshold despite a promising low-vol
regime slice (SPY low-vol Sharpe 1.986) — the grid's per-regime breakdown
shows the edge is real but confined to low-vol regimes and collapses
outright once volatility rises (high-vol pass rate 3/48 = 6.25%), and QQQ
fails every validator decisively. This mirrors this repo's other
reversal/support-resistance-style strategies that only survive in calm
regimes; a future iteration could revisit gated explicitly on a low-vol
regime filter (as done for 2026-09-03-001's Bollinger mean-reversion
strategy) rather than trading it unconditionally.
