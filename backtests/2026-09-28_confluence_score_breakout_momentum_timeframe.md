# Confluence-Score Breakout+Momentum+Timeframe Entry Filter — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_confluence_score_breakout_momentum_timeframe.py`
**Hypothesis source:** https://draconic.ai/tradecraft/confluence-scoring-method
(read via `browser_exec`; `web_extract`'s ddgs backend is search-only)

## Hypothesis

Draconic's "Confluence Scoring Method" argues stacking correlated indicators
(RSI+MACD+Stochastic, all momentum) is not real confluence — it's one
opinion counted multiple times. Genuine confluence needs INDEPENDENT signal
categories. Of the source's 5 categories (price structure, momentum
quality, flow confirmation, options positioning, timeframe alignment),
this repo's OHLCV-only data feasibility-blocks 2 (flow/options). The
remaining 3 were operationalized on daily bars: (1) rolling-N-day breakout
with volume confirmation, (2) rate-of-change acceleration (velocity
expanding vs prior window, not just "momentum positive"), (3) price above
both a daily-scale SMA and a 5x-longer weekly-scale-proxy SMA. Entry
requires `confluence_score >= min_score` (sum of the three 0/1 dimensions)
gated by an SMA uptrend filter; exit on score collapsing to 0, trend
invalidation, or a time-stop.

## Grid test (Step 6)

`param_grid={"min_score": [2, 3], "breakout_window": [20, 30]}`,
`symbols={"equity": ["QQQ"]}` (light workload, single asset class),
`vol_regime_splits=3`.

- **total_cells:** 12, **passed_cells:** 6, **pass_fraction:** 0.5
- **by_vol_regime:** low 4/4 (100%), mid 2/4 (50%), high 0/4 (0%) — the
  edge is concentrated almost entirely in the low-volatility tercile.
- **best_cell:** min_score=3, breakout_window=30, QQQ, low-vol, Sharpe
  **2.069**.
- **worst_cell:** min_score=3, breakout_window=20, QQQ, high-vol, Sharpe
  **-0.583**.

## Single-config validation (Step 7, best config min_score=3/breakout_window=30, full sample 2016-2026)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** 0.738 | **FAIL** 0.267 |
| Max Drawdown (<=0.25) | pass 0.127 | pass 0.161 |
| TC survival (net Sharpe >=0.5) | pass 0.701 | **FAIL** 0.208 |
| Walk-forward (4 splits, >=75% positive) | pass 1.0 (4/4) | **FAIL** 0.5 (2/4) |
| Parameter sensitivity (rel std <=0.5) | pass 0.242 | pass 0.415 |

## Verdict

**Rejected.** The grid's striking 100%-pass-in-low-vol / 0%-in-high-vol
split (best cell Sharpe 2.07) does not survive full-sample validation: on
the un-tercile-sliced full history, QQQ Sharpe 0.738 and SPY Sharpe 0.267
both miss the 1.0 threshold, SPY also fails TC-survival and walk-forward.
Finding: the confluence-score entry filter's edge is real but genuinely
narrow — it only earns its keep during calm/low-volatility stretches, and
because low-vol periods are a minority of the full sample, the blended
full-period Sharpe collapses well below threshold once high/mid-vol
periods (where the filter is actively negative, worst cell -0.58) are
included. This matches this repo's repeated pattern of "vol-regime-only"
near-misses (e.g. 2026-09-21-268 ZigZag breakout, 2026-09-16-180 Murrey
0/8) — the fix explored elsewhere in the KB (an explicit vol-regime GATE
added on top of the entry rule, not just implicit exposure) is a candidate
follow-up but not pursued this iteration (light workload).
