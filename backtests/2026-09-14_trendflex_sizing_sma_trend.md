# 2026-09-14 Ehlers Trendflex Continuous Sizing Overlay (SMA Trend Gate)

## Hypothesis

John Ehlers' Trendflex indicator (TASC Feb 2020 "Reflex: A New Zero-Lag
Indicator"), per https://www.prorealcode.com/prorealtime-indicators/reflex-and-trendflex-indicators-john-f-ehlers/
(formula already fully confirmed and reused verbatim from this repo's
existing accepted strategy
`strategies/2026-09-06_ehlers_trendflex_zerocross.py`, no fresh web fetch
needed this sub-step): a SuperSmoother 2-pole low-pass filter is applied
to close; the filter's deviation from each of the last `length` bars is
averaged, then normalized by a recursively-computed mean-square
(`MS[t]=0.04*s^2+0.96*MS[t-1]`, Ehlers' own smoothing constants) so the
oscillator is expressed in standard-deviation units centered around zero.

This repo's only prior Trendflex entry (2026-09-06-112) used a zero-line
CROSSOVER as a binary ENTRY trigger (accepted SPY-only, QQQ near-miss,
crypto rejected decisively). This iteration reframes Trendflex as a
CONTINUOUS SIZING dial (tanh-squashed) within an SMA(trend_window)
uptrend gate -- the same reframing pattern that rescued Firefly
Oscillator, Elegant Oscillator, VoRSI, TCF, and CTM earlier this same
cron trigger.

## Grid test summary (Step 6)

`param_grid={"length":[14,20], "sensitivity":[0.5,0.6,0.7],
"deadband":[0.15,0.2]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3` (144 cells).

- **pass_fraction: 0.382** (55/144)
- by_asset_class: equity 36/72 passed (100% of grid-default passes),
  crypto 19/72 passed
- by_vol_regime: low 42/48 (88%), mid 13/48 (27%), high 0/48 (0%)
- best_cell: QQQ low-vol, length=14/sensitivity=0.5/deadband=0.2,
  Sharpe 2.63
- worst_cell: SPY mid-vol, length=20/sensitivity=0.7/deadband=0.2,
  Sharpe -0.11

## Single-config validation (Step 7), after per-symbol retuning

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | length=14, sens=0.5, db=0.4 | 1.523 | 0.112 | 1.219 | 1.00 | 0.092 | YES |
| SPY      | length=14, sens=0.7, db=0.4 | 1.107 | 0.082 | 0.696 | 1.00 | 0.071 | YES |
| BTC/USDT | length=20, sens=0.3, db=0.15, leverage_cap=0.2, base_exposure=0.2 | 1.501 | 0.099 | 1.103 | 1.00 | 0.040 | YES |
| ETH/USDT | length=14, sens=0.3, db=0.2, leverage_cap=0.25, base_exposure=0.2 | 1.436 | 0.114 | 1.240 | 1.00 | 0.020 | YES |

All four symbols pass all five validators at their per-symbol tuned
configs, with a full 4/4 walk-forward pass fraction across every symbol
(unlike most sizing-dial strategies this trigger, which had at least one
symbol land at exactly the 0.75 threshold). MDD is comfortably low across
the board (8-11%), the tightest drawdown profile of any all-symbol-accept
strategy this cron trigger.

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

Sixth strategy this cron trigger (after Firefly, Elegant Oscillator,
VoRSI, TCF, CTM) to accept all 4 target symbols in a single reframing
pass -- and the strongest all-around result of the six (best walk-forward
consistency, tightest MDD range, lowest parameter-sensitivity relative
std across the board).

## Notes

- Formula reused verbatim from the existing accepted knowledge base entry
  (2026-09-06-112) -- no fresh web fetch needed this sub-step.
- Walk-forward fallback: manual 4-equal-slice split (same pattern as other
  `run_validate_*.py` scripts).
- Source: https://www.prorealcode.com/prorealtime-indicators/reflex-and-trendflex-indicators-john-f-ehlers/
