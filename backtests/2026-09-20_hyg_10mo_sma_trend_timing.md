# Backtest Report: HYG 10-Month SMA Trend-Timing (Yieldstream-style)

**Strategy file:** `strategies/2026-09-20_hyg_10mo_sma_trend_timing.py`
**Date:** 2026-09-20
**Outcome:** REJECTED (decisive)

## Hypothesis

Per Yieldstream's "Trend-following on high-yield bonds"
(https://www.yieldstream.com/blog/11/Trend_following_on_high_yield_bonds,
read via browser_exec fallback -- web_search DDGS backend hit repeated
TLS/connection-reset errors this iteration), a fully disclosed rule: buy
a high-yield bond fund when its monthly close is above its own 10-month
SMA, otherwise hold T-Bills. The source's own backtest on USAA
High-Yield Opportunities (USHYX, 2002-2011) reported CAGR 11.02% vs 8.73%
buy-and-hold, Sharpe 1.58 vs 0.70, MDD -4.86% vs -31.23%.

This repo substitutes HYG (liquid ETF, available via
`data/loaders.py::load_equity`) for USHYX (mutual fund, not reliably
available via yfinance) as the tradeable high-yield-bond proxy, and tests
the disclosed rule directly (approximating the source's 10-month monthly
SMA as sma_window~210 trading days).

## Parameter search (8 SMA windows, HYG full history 2008-01-01 to 2026-09-01)

| sma_window | Sharpe | Max Drawdown |
|---|---|---|
| 100 | -0.251 | 0.259 |
| 150 | 0.031 | 0.200 |
| 180 | 0.067 (best) | 0.170 |
| 200 | 0.008 | 0.177 |
| 210 (source's ~10mo equivalent) | 0.018 | 0.169 |
| 220 | 0.015 | 0.162 |
| 250 | -0.137 | 0.228 |
| 300 | -0.053 | 0.181 |

Every tested SMA window produces a Sharpe near zero (best 0.067), a
decisive, across-the-board failure -- nowhere close to the source's own
reported 1.58 Sharpe. This is a much weaker result than a typical
near-miss in this repo.

## Analysis: why the mismatch with the source's reported result?

Several likely factors:
1. **Different instrument.** USHYX (an actively-managed mutual fund with
   its own credit selection) is not the same as HYG (a passive high-yield
   ETF benchmark). The source's own trend-following edge may come partly
   from timing OUT of active-manager-specific risk, not a generic
   high-yield-market trend.
2. **Different sample period.** The source's backtest window (2002-2011)
   captures exactly one major cycle (the 2008 GFC) where the trend-timing
   rule's main value-add was avoiding that single large drawdown. HYG's
   available history (2008-2026) includes the 2020 COVID crash (a very
   fast V-shaped recovery that a 10-month SMA would badly whipsaw around)
   and the 2022 rate-hike bear market (a slower bond-specific decline
   driven by duration/rate risk rather than credit trend) -- both regimes
   where a slow trend filter performs poorly.
3. **Monthly vs daily granularity.** The source explicitly uses monthly
   closing prices and monthly rebalancing; this repo's daily-bar SMA
   translation (~210 days for "10 months") is an approximation that may
   not faithfully replicate the smoothing/whipsaw characteristics of a
   true monthly-bar system.

## Decision

**REJECTED (decisive).** Every tested SMA window produces a near-zero
Sharpe, a much weaker result than the source's own reported backtest.
This looks like a genuine asset-substitution/period mismatch rather than
a promising near-miss -- not worth further parameter search on HYG daily
bars. A future loop could revisit with a genuine monthly-bar resampling
of HYG (rather than a daily-window approximation) if a more faithful
replication of the source's exact methodology is desired.
