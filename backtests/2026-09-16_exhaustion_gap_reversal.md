# Backtest Report: Exhaustion Gap Reversal

**Date:** 2026-09-16 (iteration 9, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-16_exhaustion_gap_reversal.py`

## Hypothesis

Per a Google AI-overview summary of "Exhaustion Gap Trading Strategy For
Reversals" (Trading Setups Review, NetPicks cited): an exhaustion gap
occurs at the end of a prolonged, mature trend, accompanied by climactic
volume well above its own rolling average, signaling the trend has
exhausted and a reversal is likely. Downtrend-exhaustion-reversal (long)
variant implemented: sustained downtrend (SMA + negative slope) + gap-down
day with volume spike, confirmed by next bar closing higher, exit at
short-term MA or time-stop. First "exhaustion gap" strategy in this repo
(0 prior matches) — distinct from 2026-09-16-079 (any-size same-day gap
fade, no trend-maturity/volume gating, intraday-only hold) and
2026-09-16-085 (single-bar range/wick climax pattern, no gap component).

Source read via `browser_exec` fallback after `web_search`'s DDGS backend
continued failing with the same Yahoo/TLS RequestError seen every
iteration this trigger.

## Preliminary parameter scan (Step 6, abbreviated)

At default parameters (gap_down_threshold=0.01, volume_spike_mult=1.75),
QQQ produced only 2 trades over the full sample — too rare to evaluate
meaningfully. A loosened 9-combination scan (`gap_down_threshold ∈
{0.005,0.01,0.015}` x `volume_spike_mult ∈ {1.25,1.5,1.75}`, combinations
with >3 trades only) on QQQ found best Sharpe 0.601 (gap_down_threshold=
0.005, volume_spike_mult=1.25, 51 trades) — still well below the 1.0
threshold, and every other combination was weaker (0.34-0.55).

Extended to the most-populated config on SPY (Sharpe 0.071, 57 trades) and
crypto (BTC/USDT, ETH/USDT: **zero trades** — the sustained-downtrend +
gap-down + volume-spike compound condition essentially never co-occurs on
crypto daily bars in this construction).

Given the uniformly sub-threshold Sharpe across every equity parameter
combination and zero crypto signal, this iteration skips the full
`grid_test.py`/`validators.py` battery — the preliminary scan already
demonstrates no viable edge.

## Decision

**Reject.** No parameter combination on QQQ clears even 0.61 Sharpe (vs.
1.0 threshold); SPY is far weaker (0.07); crypto never fires. The
exhaustion-gap-plus-volume-climax construction does not translate into a
tradeable reversal signal on daily bars for this repo's asset set at any
reasonable parameterization tested. Strategy file and this report kept as
the record of a rejected attempt.
