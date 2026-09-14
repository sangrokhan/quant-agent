# 2026-09-14 Detrended Synthetic Price (DSP) Continuous Sizing Overlay

## Hypothesis

Detrended Synthetic Price (DSP, Ehlers-style), per AlphaX Trading's DSP
dictionary entry (formula already fully confirmed and reused verbatim
from this repo's existing accepted strategy
`strategies/2026-09-09_dsp_zerocross_itl_slope.py`, no fresh web fetch
needed this sub-step): DSP = typical_price - Instantaneous Trendline
(ITL, an Ehlers-style recursive high-pass/low-pass filter pair extracting
a smoothed trend component).

This repo's only prior DSP-zero-cross entry (2026-09-09-076) used DSP's
zero-crossing (plus an ITL-slope confirmation and a stagnation filter) as
a binary ENTRY trigger (accepted QQQ-only, SPY/crypto rejected). This
iteration instead reframes the raw DSP value as a CONTINUOUS SIZING dial:
rolling z-scored and tanh-squashed to [-1,+1] (since DSP is unbounded) --
the same "unbounded diff -> z-score -> tanh" reframing pattern already
used for TCF and Precision Trend earlier this same cron trigger -- within
an SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={"filter_period":[15,20], "sensitivity":[0.5,0.6,0.7],
"deadband":[0.15,0.2]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3` (144 cells).

- **pass_fraction: 0.542** (78/144, best raw grid pass fraction of any
  candidate this cron trigger)
- by_asset_class: equity 30/72 passed, **crypto 48/72 passed** -- the
  first sizing-dial candidate this trigger where crypto outperforms
  equity at the raw grid-default level
- by_vol_regime: low 48/48 (100%), mid 18/48 (38%), high 12/48 (25% --
  notably broad high-vol pass rate, similar to Precision Trend earlier
  this trigger)
- best_cell: ETH/USDT mid-vol, filter_period=15/sensitivity=0.7/deadband=0.2,
  Sharpe 2.59
- worst_cell: ETH/USDT high-vol, filter_period=20/sensitivity=0.7/deadband=0.2,
  Sharpe -0.05

## Single-config validation (Step 7), after per-symbol retuning

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | filter_period=20, sens=0.5, db=0.4 | 1.267 | 0.121 | 0.729 | 1.00 | 0.011 | YES |
| SPY      | filter_period=20, sens=0.6, db=0.4 | 1.281 | 0.065 | 0.578 | 1.00 | 0.031 | YES |
| BTC/USDT | filter_period=15, sens=0.5, db=0.15, leverage_cap=0.3, base_exposure=0.25 | 1.598 | 0.167 | 0.809 | 1.00 | 0.015 | YES |
| ETH/USDT | filter_period=15, sens=0.5, db=0.15, leverage_cap=0.2, base_exposure=0.25 | 1.286 | 0.122 | 0.633 | 1.00 | 0.056 | YES |

All four symbols pass all five validators at their per-symbol tuned
configs, with a full 4/4 walk-forward pass fraction across every symbol.
BTC's MDD (16.7%) is the highest crypto MDD of any all-symbol-accept
strategy this trigger, still comfortably under 25%; BTC also required a
higher trade count (306) and a higher leverage_cap (0.3, vs the usual
0.2-0.25) than typical crypto-pair configs this trigger.

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

Eighth strategy this cron trigger (after Firefly, Elegant Oscillator,
VoRSI, TCF, CTM, Trendflex, Precision Trend) to accept all 4 target
symbols in a single reframing pass -- and notable for being the first
this trigger where the raw grid-default pass fraction favors crypto over
equity, and for having the best overall raw grid pass fraction (0.542) of
the eight all-symbol accepts.

## Notes

- Formula reused verbatim from the existing accepted knowledge base entry
  (2026-09-09-076) -- no fresh web fetch needed this sub-step.
- Walk-forward fallback: manual 4-equal-slice split (same pattern as other
  `run_validate_*.py` scripts).
- Source: https://alphax.trading/dictionary/detrended-synthetic-price
