# 2026-09-14 Trend Continuation Factor (TCF) Diff Continuous Sizing Overlay

## Hypothesis

Trend Continuation Factor (TCF, M.H. Pee, TASC Mar 2001), per ProRealCode's
disclosed PRT source (formula already fully confirmed and reused verbatim
from this repo's existing accepted strategy
`strategies/2026-09-08_tcf_crossover_pee.py`, no fresh web fetch needed
this sub-step):

    r = ROC(1, close)                      -- 1-bar difference
    pc = max(r, 0); nc = max(-r, 0)
    ncf, pcf = running cumulative sums of nc, pc, each RESET to 0
               whenever nc==0 / pc==0 respectively
    TCF+ = SUM(pc, sumperiod) - SUM(ncf, sumperiod)
    TCF- = SUM(nc, sumperiod) - SUM(pcf, sumperiod)

This repo's only prior TCF entry (2026-09-08-027) used the TCF+/TCF-
CROSSOVER as a binary ENTRY trigger (accepted QQQ-only, SPY near-miss,
crypto rejected decisively). This iteration instead reframes the signed
diff (TCF+ - TCF-) as a CONTINUOUS SIZING dial: rolling z-scored and
tanh-squashed to [-1,+1] (since the raw diff is unbounded, unlike the
naturally-bounded oscillators used earlier this trigger for Firefly/
Elegant/VoRSI) within an SMA(trend_window) uptrend gate -- the same
"unbounded diff -> z-score -> tanh" reframing pattern already used for
Vortex-diff-ratio/DMI-diff/RWI-diff elsewhere in this repo.

## Grid test summary (Step 6)

`param_grid={"sumperiod":[25,35], "sensitivity":[0.5,0.6,0.7],
"deadband":[0.15,0.2]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3` (144 cells).

- **pass_fraction: 0.417** (60/144)
- by_asset_class: equity 36/72 passed, crypto 24/72 passed
- by_vol_regime: low 46/48 (96%), mid 14/48 (29%), high 0/48 (0% -- edge
  concentrated in low/mid volatility, consistent with nearly every other
  trend-following sizing-dial strategy in this repo)
- best_cell: QQQ low-vol, sumperiod=35/sensitivity=0.6/deadband=0.15,
  Sharpe 3.00
- worst_cell: SPY mid-vol, sumperiod=35/sensitivity=0.6/deadband=0.2,
  Sharpe -0.21

## Single-config validation (Step 7), after per-symbol retuning

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | sumperiod=35, sens=0.6, db=0.4 | 1.392 | 0.146 | 1.187 | 0.75 | 0.035 | YES |
| SPY      | sumperiod=25, sens=0.5, db=0.4 | 1.009 | 0.116 | 0.685 | 0.75 | 0.032 | YES |
| BTC/USDT | sumperiod=35, sens=0.3, db=0.15, leverage_cap=0.2, base_exposure=0.2 | 1.586 | 0.128 | 1.199 | 1.00 | 0.028 | YES |
| ETH/USDT | sumperiod=25, sens=0.3, db=0.15, leverage_cap=0.2, base_exposure=0.2 | 1.192 | 0.108 | 0.939 | 1.00 | 0.060 | YES |

All four symbols pass all five validators at their per-symbol tuned
configs. Equity used a widened deadband (0.4 vs the 0.15-0.2 grid
default) for transaction-cost survival; crypto used the now-standard
leverage-cap-aware low-exposure recalibration (base_exposure=0.2,
leverage_cap=0.2, lower sensitivity=0.3) to keep MDD under 25%.

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

Fourth strategy this cron trigger (after Firefly, Elegant Oscillator,
VoRSI) to accept all 4 target symbols in a single reframing pass. QQQ's
MDD (14.6%) is the highest of the four "all-symbol accepts" this trigger,
still comfortably within the 25% threshold.

## Notes

- Formula reused verbatim from the existing accepted knowledge base entry
  (2026-09-08-027) -- no fresh web fetch needed this sub-step.
- Walk-forward fallback: manual 4-equal-slice split (same pattern as other
  `run_validate_*.py` scripts).
- Source: https://www.prorealcode.com/prorealtime-indicators/trend-continuation-factor/
