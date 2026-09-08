# Backtest Report: Ehlers Reflex Cycle-Trough Mean-Reversion

**Strategy file:** `strategies/2026-09-08_ehlers_reflex_cycle_trough_meanrev.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Per ProRealCode's transcription of John Ehlers' "Reflex: A New Zero-Lag
Indicator" (TASC Feb 2020) (https://www.prorealcode.com/prorealtime-indicators/reflex-and-trendflex-indicators-john-f-ehlers/):
Reflex is the cycle-synchronized companion to the already-accepted
Trendflex oscillator (2026-09-06-112, accepted SPY only). Both apply a
2-pole SuperSmoother filter, but Reflex first detrends via an estimated
linear slope before normalizing deviations, isolating the CYCLE component
rather than the trend component. We tested Reflex as a mean-reversion
signal on its own cyclic troughs (long entry on Reflex recovering from
below an oversold threshold, exit at an overbought threshold or
time-stop), on QQQ/SPY (equity) and BTC/USDT, ETH/USDT (crypto). First
Reflex-family entry in this repo.

## Step 6 — Grid test summary

Grid: `length` in {14, 20, 30} x `max_hold_days` in {10, 15, 20},
QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto), 3 vol-regime terciles,
2019-01-01 to 2026-09-01. 108 cells total.

- **pass_fraction: 0.083** (9/108 cells) — weakest grid result of this
  cron trigger's four iterations
- **by_asset_class:** equity 9/54 passed; crypto 0/54 (decisive fail)
- **by_vol_regime:** low 7/36; mid 2/36; high 0/36
- **best_cell:** SPY, length=14, max_hold_days=20, low-vol, Sharpe 1.90
- **worst_cell:** QQQ, length=14, max_hold_days=10, mid-vol, Sharpe -1.00

## Decision: REJECT (no further validator suite run)

Full-sample Sharpe check on the best config (SPY, length=14,
max_hold_days=20, 2019-2026): **0.472**, decisively below the 1.0
threshold — not a borderline near-miss worth the full validator suite.
The grid's own weak pass_fraction (0.083, lowest of this trigger's four
tests) and the fact that even the best cell's edge doesn't survive to
full-sample confirms this is a clear reject. Crypto rejected decisively
(0/54 grid cells). Consistent with the Trendflex/Reflex sibling-indicator
pattern already observed in this repo: Trendflex's trend-component
construction found a real (if narrow, SPY-only) edge, but Reflex's
cycle-trough-mean-reversion reinterpretation does not.
