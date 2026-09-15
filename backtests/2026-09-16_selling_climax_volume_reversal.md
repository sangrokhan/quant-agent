# Backtest Report: Selling-Climax Volume Reversal

**Date:** 2026-09-16 (iteration 8, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-16_selling_climax_volume_reversal.py`

## Hypothesis

Per a Google AI-overview summary ("Strategy Rules and Mechanics", Smart
Money/Trading Philosophy YouTube channels cited): identify trend bottoms
via a Wyckoff-style selling-climax bar -- prior downtrend (close below
rolling SMA), a single bar with volume >= 3-5x its own rolling average AND
elevated true range, closing in the upper portion of its own range
(absorption/long-lower-wick signature), confirmed by the next bar closing
higher. Exit at a short-term moving-average mean-reversion target or a
time-stop. First "climax volume"/selling-climax-reversal strategy in this
repo (0 prior matches) -- distinct from all prior continuous volume-flow
oscillators (OBV, Klinger, Chaikin, Force Index, Demand Index) since this
is a single-bar event-detection pattern gated by a prior downtrend, not a
continuous indicator.

Source read via `browser_exec` fallback after `web_search`'s DDGS backend
continued failing with the same Yahoo/TLS RequestError seen every
iteration this trigger.

## Preliminary parameter scan (Step 6, abbreviated)

At the strategy's literal source-default parameters (volume_spike_mult=3.0,
close_position_min=0.6), QQQ produced **zero trades** over the 2019-2026
sample — the compound AND-condition (downtrend + 3x volume spike + 1.5x
range spike + strong absorption + next-bar confirmation) is too strict to
ever fire together on daily bars for this symbol.

Loosened to a 27-combination scan (`volume_spike_mult ∈ {1.5,2.0,2.5}` x
`range_spike_mult ∈ {1.0,1.2,1.5}` x `close_position_min ∈ {0.4,0.5,0.6}`)
on QQQ: **every single combination produced a negative Sharpe** (-0.08 to
-0.18), 18-102 trades depending on looseness.

Extended to SPY, BTC/USDT, ETH/USDT at the most-populated loosened config
(volume_spike_mult=1.5, range_spike_mult=1.0, close_position_min=0.5):
SPY -0.033, BTC/USDT 0.427 (best of all tests, still far below 1.0),
ETH/USDT 0.163.

Given the uniformly negative-to-weak Sharpe across every parameter
combination and symbol tested (27+3 = 30 data points, none above 0.43),
this iteration skips the full `grid_test.py`/`validators.py` battery as a
poor use of budget — the preliminary scan already demonstrates no viable
edge exists in this event-detection construction on daily bars.

## Decision

**Reject.** The selling-climax pattern, as constructed here on daily OHLCV
bars, shows no exploitable edge — likely because a genuine single-bar
"climax" event is fundamentally an INTRADAY phenomenon (the source's own
example bar shape — a long lower wick with a strong close — describes
price action that occurs and reverses WITHIN one trading session, which a
daily close-to-close return series only partially captures). Strategy file
and this report kept as the record of a rejected attempt; note for future
iterations: this pattern may be more promising if this repo ever gains
intraday-bar capability for equities/crypto.
