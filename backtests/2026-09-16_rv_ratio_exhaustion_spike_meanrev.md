# Backtest Report: Realized-Volatility Ratio Exhaustion-Spike Mean Reversion

**Date:** 2026-09-16 (iteration 7, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-16_rv_ratio_exhaustion_spike_meanrev.py`

## Hypothesis

Companion to 2026-09-16-083 (compression regime), testing the other half
of the same source's RV_ratio construction: RV_ratio (RV_short(10d)/
RV_long(90d)) spiking above `spike_threshold` (source's own examples:
2.0-2.5, or the 95th percentile of its own rolling history) signals a
panic/forced-liquidation "exhaustion spike" that historically mean-reverts.
Source's own trade is short-volatility (short the spiking asset); this
long-only adaptation (SAFETY.md) instead buys the panic: long when RV_ratio
spikes AND the preceding `panic_lookback`-day return confirms a selloff,
betting on the bounce as vol normalizes; exit when RV_ratio reverts below
`exit_threshold` or a time-stop.

## Preliminary parameter scan (Step 6, abbreviated — see rationale below)

A quick manual scan across `spike_threshold in {1.5,1.75,2.0}` x
`panic_drop_threshold in {-0.01,-0.02,-0.03}` on QQQ found Sharpe ranging
from -0.37 to +0.13 across all 9 combinations — no configuration shows
meaningful edge (all near zero, several negative). Extended to SPY
(Sharpe -0.02, 66 trades) and BTC/USDT (Sharpe 0.62, 101 trades — the one
mildly promising cell) at the most balanced config
(spike_threshold=1.75, panic_drop_threshold=-0.02).

Given the near-uniformly-flat-to-negative Sharpe across every tested
parameter combination and symbol (only BTC/USDT shows even a weak positive
signal, well below the 1.0 threshold), this iteration skips the full
`grid_test.py`/`validators.py` battery as a poor use of budget — the
preliminary scan already demonstrates no viable edge exists in this
construction at any reasonable parameterization tested.

## Decision

**Reject.** No parameter combination tested (9 QQQ combos + SPY + BTC/USDT
spot-checks) produces a Sharpe anywhere near the 1.0 acceptance threshold;
most cluster near zero, several are negative. The panic-selloff + vol-spike
combination does not translate into a tradeable mean-reversion bounce on
daily bars for this repo's asset set, at least not via the simple
threshold-crossing construction tested here. Strategy file and this report
kept as the record of a rejected attempt.
