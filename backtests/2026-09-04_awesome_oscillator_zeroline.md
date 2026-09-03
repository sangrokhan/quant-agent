# Awesome Oscillator Zero-Line Crossover (SMA200 trend-confirmed) — Backtest Report

**Hypothesis** (kb id 2026-09-04-041): Bill Williams' Awesome Oscillator
(AO = SMA(5, median price) - SMA(34, median price)) crossing from below to
above zero signals a shift toward bullish momentum, confirmed by a
SMA(200) uptrend filter per the source's own recommendation to verify an
existing uptrend before trusting the crossover. Exit on the opposing
zero-line cross.

**Source**: Google AI-overview + https://www.quantifiedstrategies.com/bill-williams-awesome-oscillator-strategy/
(web_search failed 5x with a DDGS/Yahoo TLS connection error this
iteration, fell back to browser_exec immediately per loop-avoidance rule).

## Grid test (Step 6)

`param_grid = {ao_fast: [5], ao_slow: [34], trend_window: [50,200]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3,
2019-01-01 to 2026-09-01. 24 total cells.

- pass_fraction: **0.167** (4/24)
- by_asset_class: equity 4/12, crypto 0/12
- by_vol_regime: low 4/8, mid 0/8, high 0/8

Full-sample sweep across both trend_window values before selecting a
primary config (per the lesson from the prior iteration's Vortex strategy):
QQQ trend_window=50 Sharpe 0.554, trend_window=200 Sharpe 0.893; SPY
trend_window=50 Sharpe 0.641, trend_window=200 Sharpe 0.867.
trend_window=200 is clearly better on both symbols -- selected as primary.

## Full-sample validators (Step 7) — primary config (ao_fast=5, ao_slow=34, trend_window=200)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Trades |
|---|---|---|---|---|
| QQQ | 0.893 (fail, thr 1.0) | 0.200 (pass, thr 0.25) | 0.857 (pass, thr 0.5) | 24 |
| SPY | 0.867 (fail, thr 1.0) | 0.125 (pass) | 0.814 (pass) | 24 |

## Decision: REJECTED (near-miss on both QQQ and SPY)

Both symbols fail only on Sharpe (QQQ 0.893, a 10.7% shortfall; SPY 0.867,
a 13.3% shortfall) -- MDD and transaction-cost survival both pass
comfortably on both. Neither is a decisive rejection, but neither clears
the bar either, and unlike the Coppock Curve accept two iterations ago,
there was no parameter (within the tested range) that pushed Sharpe over
1.0 while keeping trades reasonable -- trend_window=200 was already the
better of the two tested and still falls short. Crypto rejected decisively
(0/12 grid cells). A future loop could try adding the source's "saucer"
pattern confirmation (a specific 3-bar histogram shape, not implemented
here) as an additional filter to reduce false zero-line crosses.
