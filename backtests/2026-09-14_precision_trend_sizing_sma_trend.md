# 2026-09-14 Ehlers Precision Trend Continuous Sizing Overlay

## Hypothesis

John Ehlers' "Precision Trend Analysis" (TASC Aug/Sep 2024 Traders' Tips),
per https://financial-hacker.com/ehlers-precision-trend-analysis/ (formula
already fully confirmed and reused verbatim from this repo's existing
accepted strategy `strategies/2026-09-12_ehlers_precision_trend.py`, no
fresh web fetch needed this sub-step): a 3-pole highpass filter
(`HighPass3`, pole angle f=1.414*pi/Length) is applied to price at two
different lengths (Length1 > Length2); their DIFFERENCE is Ehlers' own
near-zero-lag "Trend" line.

This repo's only prior Precision Trend entry (2026-09-12-171) used the
Trend line's rate-of-change (TROC) turning-point (peak/valley) crossings
as a binary ENTRY trigger (accepted SPY-only, QQQ/crypto rejected
decisively). This iteration instead reframes the raw Trend line itself as
a CONTINUOUS SIZING dial: rolling z-scored and tanh-squashed to [-1,+1]
(since the raw dual-highpass difference is unbounded) within an
SMA(trend_window) uptrend gate -- the same "unbounded diff -> z-score ->
tanh" reframing pattern already used for TCF earlier this same cron
trigger.

## Grid test summary (Step 6)

`param_grid={"length1":[150,250], "sensitivity":[0.5,0.6,0.7],
"deadband":[0.15,0.2]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3` (144 cells).

- **pass_fraction: 0.479** (69/144)
- by_asset_class: equity 36/72 passed, crypto 33/72 passed
- by_vol_regime: low 38/48 (79%), mid 19/48 (40%), high 12/48 (25% -- a
  notably broader high-vol pass rate than almost any other sizing-dial
  strategy this trigger, which typically pass 0-4/48 in high vol)
- best_cell: QQQ low-vol, length1=250/sensitivity=0.6/deadband=0.15,
  Sharpe 2.90
- worst_cell: QQQ high-vol, length1=250/sensitivity=0.5/deadband=0.2,
  Sharpe -0.42

## Single-config validation (Step 7), after per-symbol retuning

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | length1=150, sens=0.6, db=0.4 | 1.361 | 0.160 | 1.166 | 0.75 | 0.022 | YES |
| SPY      | length1=150, sens=0.7, db=0.2 | 1.093 | 0.107 | 0.633 | 0.75 | 0.032 | YES |
| BTC/USDT | length1=150, sens=0.3, db=0.15, leverage_cap=0.2, base_exposure=0.2 | 1.411 | 0.106 | 1.079 | 1.00 | 0.027 | YES |
| ETH/USDT | length1=150, sens=0.3, db=0.15, leverage_cap=0.2, base_exposure=0.2 | 1.193 | 0.121 | 0.949 | 1.00 | 0.025 | YES |

All four symbols pass all five validators at their per-symbol tuned
configs. QQQ's MDD (16.0%) is the highest of any all-symbol-accept
strategy this trigger, still comfortably under the 25% threshold.

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

Seventh strategy this cron trigger (after Firefly, Elegant Oscillator,
VoRSI, TCF, CTM, Trendflex) to accept all 4 target symbols in a single
reframing pass. Notable for the unusually broad high-vol-tercile grid pass
rate (25% vs the typical 0-8% for other sizing-dial strategies this
trigger) -- worth flagging for a future iteration exploring whether the
dual-highpass-difference construction generalizes better across
volatility regimes than the z-score/tanh oscillators tried elsewhere.

## Notes

- Formula reused verbatim from the existing accepted knowledge base entry
  (2026-09-12-171) -- no fresh web fetch needed this sub-step.
- Walk-forward fallback: manual 4-equal-slice split (same pattern as other
  `run_validate_*.py` scripts).
- Source: https://financial-hacker.com/ehlers-precision-trend-analysis/
