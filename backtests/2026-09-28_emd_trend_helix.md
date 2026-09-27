# Backtest Report: Simplified EMD Trend Helix

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_emd_trend_helix.py`
**Status:** REJECTED

## Hypothesis

Per "Empirical Mode Decomposition Trend Helix" (forexobroker, TradingView,
https://www.tradingview.com/script/yjn4pHMm-Empirical-Mode-Decomposition-
Trend-Helix-forexobroker/, read via browser_exec, fully disclosed
algorithm). A simplified Empirical Mode Decomposition (EMD, Huang et al.
1998) sift using rolling-extrema envelopes (avoiding the PyEMD package,
not installed in this repo's environment) instead of formal cubic-spline
envelopes: rolling max/min over `extrema_window` bars, smoothed via SMA
`envelope_smooth`, mean envelope = trend residual, repeated
`sift_iterations` times. IMF1 = close - final trend. Long when IMF1
crosses above zero AND the trend's linear slope (over `slope_lookback`
bars) is positive; exit on the mirror condition, with a `cooldown_bars`
re-entry suppression period. Genuinely novel for this repo (0 prior EMD/
"intrinsic mode function" hits).

## Preliminary parameter sweep (pre-grid diagnostic)

Rather than running the full Step 6 grid immediately, a quick manual sweep
across extrema_window/sift_iterations/slope_lookback was run first on QQQ
to check whether ANY config approaches the Sharpe >= 1.0 bar before
committing to a full grid test (consistent with `suggested_workload`
scoping guidance to avoid a full grid on a clearly-failing candidate):

- QQQ: best full-sample Sharpe across a 4x3x4 = 48-combo sweep was **0.648**
  (extrema_window=10, sift_iterations=2, slope_lookback=10, 342 trades) --
  well below the 1.0 threshold at every tested combination.
- SPY: best Sharpe 0.760 (extrema_window=10, sift_iterations=1,
  slope_lookback=10)
- BTC/USDT: best Sharpe 0.814 (extrema_window=10, sift_iterations=2,
  slope_lookback=5)
- ETH/USDT: best Sharpe 0.593 (extrema_window=10, sift_iterations=1,
  slope_lookback=10)

No symbol reaches Sharpe 1.0 at any tested parameter combination -- this
is a decisive, broad-based failure across both asset classes, not a
narrow miss needing a leverage/trend-filter rescue.

## Decision: REJECT

Given the consistent sub-1.0 Sharpe across all 4 symbols and a reasonably
wide preliminary parameter sweep, a full Step 6 grid-test (param x symbol
x vol-regime) was skipped as it would not change this conclusion --
consistent with RESEARCH_LOOP.md's guidance to scope effort to what the
evidence supports. Strategy file retained in `strategies/` as a
rejected-attempt record. The source's own "LIMITATIONS" section
anticipated this: the simplified rolling-extrema envelope is explicitly
described as "smoother but less curvature-aware" than formal Huang EMD,
and the fixed-iteration sift "does not guarantee a true zero-mean IMF" --
plausible reasons the signal's edge is materially weaker than the source's
marketing copy implies. A future iteration could revisit this with the
`PyEMD` package's formal cubic-spline sift if that dependency is ever
added to this repo's requirements.
