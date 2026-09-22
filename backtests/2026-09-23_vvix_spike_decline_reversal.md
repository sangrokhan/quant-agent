# VVIX Spike-and-Decline Reversal Signal (SPY/QQQ)

**Date:** 2026-09-23 | **Strategy file:** `strategies/2026-09-23_vvix_spike_decline_reversal.py`

## Hypothesis

Per https://tosindicators.com/research/using-the-vvix-to-trade-spy (visited
this iteration), VVIX (CBOE's "volatility of volatility", expected 30-day
vol of the VIX itself) spiking above 120 then DECLINING from that spike
("the VVIX often collapses within days even if the VIX remains elevated")
marks a leading indicator for SPY bottoms/reversals, per the source's own
historical case studies (Feb 2018 Volmageddon, Dec 2018 Fed pause, Mar 2020
COVID low -- VVIX peaked and reversed BEFORE SPY found its low each time).
First absolute-level-threshold VVIX strategy in this repo (distinct from
2026-09-10-042's VVIX/VIX-RATIO-vs-SMA regime gate).

## Grid summary (`grid_summary_vvix_spike_decline.json`)

- 96 cells: `spike_threshold` in {110,120} x `decline_lookback` in {3,5} x
  `normal_threshold` in {90,95} x `max_hold_days`={20}, QQQ/SPY/BTCUSDT/
  ETHUSDT, vol_regime_splits=3.
- **pass_fraction: 0.125 (12/96)** -- weak from the outset.
- by_asset_class: equity 8/48, crypto 4/48.
- by_vol_regime: **low 12/32, mid 0/32, high 0/32** (only passes in the
  calmest tercile, which is also where VVIX spikes above 120 are rarest --
  an internally inconsistent finding since the strategy's own entry
  condition requires an extreme-fear VVIX spike, which by construction
  should co-occur with higher-vol periods, yet those are exactly where it
  fails).
- best_cell: SPY, spike_threshold=120, decline_lookback=3,
  normal_threshold=90, low-vol, Sharpe 1.24.

## Single-config validators (best_cell params, full-sample 2016-2026)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| SPY | 0.42 (FAIL, thr 1.0) | 0.287 (FAIL, thr 0.25) | 0.346 (FAIL, thr 0.5) | 1.0 (PASS) | 0.07 (PASS) |
| QQQ | 0.42 (FAIL) | 0.243 (PASS, near-miss) | 0.355 (FAIL) | 0.75 (PASS, borderline) | 0.47 (PASS, near-miss) |

## Decision: REJECTED

Both symbols fail Sharpe and tx-cost survival; SPY additionally fails MDD
decisively. Only 74 trades over a 10-year sample (VVIX>120 spikes are
genuinely rare events, ~254 trading days out of 2500), so the strategy is
event-driven and thin -- the grid's low-vol-only pass pattern plus the weak
full-sample metrics suggest the source's narrative (a handful of famous
historical VVIX spike-reversal episodes) does not generalize into a
systematically profitable mechanical rule once transaction costs and the
full sample (including the very vol spikes the signal is designed to
trade) are accounted for.
