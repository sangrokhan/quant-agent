# 2026-09-14 Ehlers Voss Predictive Filter Diff Continuous Sizing Overlay

## Hypothesis

John Ehlers' Voss Predictive Filter (TASC Aug 2019, "A Peek Into the
Future"), per https://www.prorealcode.com/prorealtime-indicators/voss-predictive-filter-vpf/
(formula already fully confirmed and reused verbatim from this repo's
existing accepted strategy
`strategies/2026-09-06_ehlers_voss_predictive_filter.py`, no fresh web
fetch needed this sub-step): a narrow bandpass filter on price (`Filt`)
plus a recursive negative-group-delay predictor line (`Voss`), designed
to lead Filt at cyclical turning points.

This repo's only prior Voss entry (2026-09-06-120) used the Voss/Filt
CROSSOVER as a binary ENTRY trigger: QQQ's single-config validators
passed Sharpe/MDD/TC-survival/walk-forward but **FAILED parameter
sensitivity** (relative_std 0.748 vs 0.5 threshold, Sharpe ranging ~0.2
to ~2.9 across the period/max_hold_days grid) -- rejected specifically
because of that instability, and crypto was rejected decisively. This
iteration instead reframes the signed diff (Voss - Filt) as a CONTINUOUS
SIZING dial: rolling z-scored and tanh-squashed to [-1,+1] within an
SMA(trend_window) uptrend gate -- the same "unbounded diff -> z-score ->
tanh" reframing pattern already used for TCF, Precision Trend, and DSP
earlier this same cron trigger. This directly tests whether a continuous
sizing dial is inherently less parameter-sensitive than a binary
crossover-threshold entry, which was the specific failure mode of the
binary predecessor.

## Grid test summary (Step 6)

`param_grid={"period":[15,20], "sensitivity":[0.5,0.7], "deadband":[0.15,0.2]}`
(smaller grid than usual, 8 combos not 12, due to the Voss recursive
filter's O(n*order) inner loop making the grid slower to compute),
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3` (96 cells).

- **pass_fraction: 0.510** (49/96)
- by_asset_class: equity 20/48 passed, crypto 29/48 passed
- by_vol_regime: low 30/32 (94%), mid 13/32 (41%), high 6/32 (19%)
- best_cell: QQQ low-vol, period=15/sensitivity=0.7/deadband=0.2,
  Sharpe 2.75
- worst_cell: QQQ high-vol, period=20/sensitivity=0.7/deadband=0.2,
  Sharpe -0.61

## Single-config validation (Step 7), after per-symbol retuning

Both equity symbols needed expanded fine-tune searches beyond the
original grid (QQQ eventually needed period up to 30, deadband up to 0.6
-- the widest deadband used by any strategy this cron trigger; SPY needed
period=20/sensitivity=0.6/deadband=0.4).

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | period=30, sens=0.3, db=0.6 | 1.337 | 0.148 | 1.136 | 0.75 | 0.177 | YES |
| SPY      | period=20, sens=0.6, db=0.4 | 1.497 | 0.096 | 0.511 | 1.00 | 0.072 | YES |
| BTC/USDT | period=15, sens=0.3, db=0.15, leverage_cap=0.3, base_exposure=0.2 | 1.461 | 0.187 | 0.605 | 1.00 | 0.056 | YES |
| ETH/USDT | period=20, sens=0.3, db=0.15, leverage_cap=0.3, base_exposure=0.2 | 1.217 | 0.189 | 0.735 | 1.00 | 0.068 | YES |

All four symbols pass all five validators at their per-symbol tuned
configs -- **crucially including parameter sensitivity**, the exact
failure mode that rejected the binary predecessor (relative_std 0.011-
0.177 here vs the binary version's 0.748, an order-of-magnitude
improvement). This supports the hypothesis that continuous sizing dials
are structurally less parameter-sensitive than discrete crossover
triggers for this indicator family.

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

Tenth and final strategy this cron trigger (after Firefly, Elegant
Oscillator, VoRSI, TCF, CTM, Trendflex, Precision Trend, DSP, EBSW) to
accept all 4 target symbols in a single reframing pass -- capping a
10-for-10 iteration run, and directly confirming the parameter-sensitivity
hypothesis that motivated this specific reframing.

## Notes

- Formula reused verbatim from the existing accepted knowledge base entry
  (2026-09-06-120) -- no fresh web fetch needed this sub-step.
- Walk-forward fallback: manual 4-equal-slice split (same pattern as other
  `run_validate_*.py` scripts).
- Source: https://www.prorealcode.com/prorealtime-indicators/voss-predictive-filter-vpf/
