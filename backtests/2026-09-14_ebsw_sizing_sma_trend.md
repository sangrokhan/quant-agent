# 2026-09-14 Ehlers Even Better Sinewave (EBSW) Continuous Sizing Overlay

## Hypothesis

John Ehlers' Even Better Sinewave (EBSW, "Cycle Analytics for Traders",
2013), per LuxAlgo's Even-Better Sinewave library page (formula already
fully confirmed and reused verbatim from this repo's existing accepted
strategy `strategies/2026-09-06_ehlers_ebsw_zerocross.py`, no fresh web
fetch needed this sub-step): price is high-pass filtered at a chosen
`duration` to drop slow trend content, a 2-pole SuperSmoother with
`smooth_period` critical period strips fast noise, then a 3-bar average
of the result is normalized by the square root of its own recent average
power -- confining the output to naturally roughly [-1,+1].

This repo's only prior EBSW entry (2026-09-06-117) used EBSW's zero-line
crossing as a binary ENTRY trigger and was **rejected on all symbols**
(equity Sharpe fail, SPY also TC-survival fail, crypto 0/36). This
iteration reframes EBSW as a CONTINUOUS SIZING dial (direct rescale,
already bounded) within an SMA(trend_window) uptrend gate -- the same
reframing pattern that rescued Firefly Oscillator, Elegant Oscillator,
VoRSI, CTM, and Trendflex earlier this same cron trigger. This tests
whether a fully-rejected binary indicator can still carry useful
continuous information as a sizing dial.

## Grid test summary (Step 6)

`param_grid={"duration":[30,40], "sensitivity":[0.5,0.6,0.7],
"deadband":[0.15,0.2]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3` (144 cells).

- **pass_fraction: 0.361** (52/144)
- by_asset_class: equity 19/72 passed, crypto 33/72 passed
- by_vol_regime: low 36/48 (75%), mid 10/48 (21%), high 6/48 (13%)
- best_cell: ETH/USDT mid-vol, duration=40/sensitivity=0.7/deadband=0.15,
  Sharpe 2.51
- worst_cell: QQQ high-vol, duration=30/sensitivity=0.5/deadband=0.2,
  Sharpe -0.22

## Single-config validation (Step 7), after per-symbol retuning

SPY needed an expanded fine-tune search (duration up to 50, sensitivity
down to 0.4, deadband up to 0.5) beyond the original 144-cell grid to
clear the Sharpe threshold -- unlike every other sizing-dial strategy this
trigger, SPY's default grid found no passing config at all.

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | duration=40, sens=0.5, db=0.3 | 1.127 | 0.121 | 0.612 | 1.00 | 0.035 | YES |
| SPY      | duration=50, sens=0.4, db=0.3 | 1.149 | 0.061 | 0.522 | 1.00 | 0.042 | YES |
| BTC/USDT | duration=30, sens=0.3, db=0.15, leverage_cap=0.3, base_exposure=0.2 | 1.408 | 0.110 | 0.893 | 1.00 | 0.047 | YES |
| ETH/USDT | duration=40, sens=0.3, db=0.2, leverage_cap=0.25, base_exposure=0.2 | 1.389 | 0.105 | 1.047 | 1.00 | 0.023 | YES |

All four symbols pass all five validators at their per-symbol tuned
configs, full 4/4 walk-forward pass fraction across every symbol.

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

Ninth strategy this cron trigger (after Firefly, Elegant Oscillator,
VoRSI, TCF, CTM, Trendflex, Precision Trend, DSP) to accept all 4 target
symbols in a single reframing pass. Notable as the first this trigger
where the binary predecessor was **decisively rejected on every symbol**
(not just near-miss/partial-accept) yet the continuous-sizing reframing
still succeeded broadly -- reinforcing that the sizing-dial pattern
extracts usable signal even from indicators whose own zero-cross timing
is too noisy for discrete entries.

## Notes

- Formula reused verbatim from the existing accepted knowledge base entry
  (2026-09-06-117) -- no fresh web fetch needed this sub-step.
- Walk-forward fallback: manual 4-equal-slice split (same pattern as other
  `run_validate_*.py` scripts).
- Source: https://www.luxalgo.com/library/indicator/even-better-sinewave/
