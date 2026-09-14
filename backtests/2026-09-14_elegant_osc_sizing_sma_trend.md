# 2026-09-14 Elegant Oscillator (Inverse Fisher Transform) Continuous Sizing Overlay

## Hypothesis

Ehlers Elegant Oscillator (Inverse Fisher Transform), per John F. Ehlers'
TASC February 2022 article, reproduced at
https://financial-hacker.com/the-inverse-fisher-transform/ (formula
already verified with fully-disclosed C code by this repo's prior
strategy `strategies/2026-09-12_elegant_oscillator_meanrev.py`, re-used
without a fresh fetch since the exact construction was already confirmed
and logged in this repo):

    deriv[t]      = price[t] - price[t-2]
    rms[t]        = sqrt(mean(deriv[t-length+1..t]^2))
    norm_deriv[t] = deriv[t] / rms[t]
    ift(x)        = (exp(2x) - 1) / (exp(2x) + 1)   -- naturally [-1,+1]
    EO[t]         = SuperSmoother(ift(norm_deriv), smooth_length)[t]

The Inverse Fisher Transform construction guarantees EO stays in [-1,+1]
by design. This repo's only prior Elegant Oscillator entry used EO as a
MEAN-REVERSION peak/valley-threshold ENTRY trigger (accepted SPY only,
QQQ rejected on parameter sensitivity, crypto rejected decisively). This
iteration instead reframes EO as a CONTINUOUS SIZING dial within an
SMA(trend_window) uptrend gate -- same reframing pattern that has
repeatedly rescued binary-only bounded oscillators elsewhere in this repo
(BOP, CHOP, VZO, Vortex-diff-ratio, TSI, RMI, SMI, STARC, Firefly earlier
this same cron trigger). First Elegant-Oscillator continuous-sizing
variant, and first TREND-FOLLOWING (rather than mean-reversion) use of
this indicator in this repo.

## Grid test summary (Step 6)

`param_grid={"length":[15,20], "sensitivity":[0.5,0.6,0.7],
"deadband":[0.15,0.2]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3` (144 cells).

- **pass_fraction: 0.500** (72/144)
- by_asset_class: equity 36/72 passed, crypto 36/72 passed (perfectly
  balanced across asset classes at grid defaults, before per-symbol
  retuning -- best raw balance of any sizing-dial candidate tested this
  cron trigger)
- by_vol_regime: low 48/48 (100%), mid 24/48 (50%), high 0/48 (0% -- edge
  concentrated in low/mid volatility, consistent with nearly every other
  trend-following sizing-dial strategy in this repo)
- best_cell: QQQ low-vol, length=15/sensitivity=0.5/deadband=0.2,
  Sharpe 2.71
- worst_cell: QQQ high-vol, length=20/sensitivity=0.7/deadband=0.2,
  Sharpe -0.20

## Single-config validation (Step 7), after per-symbol retuning

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | length=20, sens=0.6, db=0.3 | 1.390 | 0.112 | 0.897 | 1.00 | 0.039 | YES |
| SPY      | length=20, sens=0.6, db=0.3 | 1.033 | 0.061 | 0.504 | 0.75 | 0.023 | YES |
| BTC/USDT | length=15, sens=0.3, db=0.2, leverage_cap=0.25, base_exposure=0.2 | 1.487 | 0.123 | 1.164 | 1.00 | 0.003 | YES |
| ETH/USDT | length=20, sens=0.3, db=0.2, leverage_cap=0.25, base_exposure=0.2 | 1.304 | 0.119 | 1.122 | 1.00 | 0.001 | YES |

All four symbols pass all five validators at their per-symbol tuned
configs. Equity used a widened deadband (0.3 vs the 0.15-0.2 grid
default) for transaction-cost survival; crypto used the now-standard
leverage-cap-aware low-exposure recalibration (base_exposure=0.2,
leverage_cap=0.25, lower sensitivity=0.3) to keep MDD under 25%.

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

Second strategy this cron trigger (after Firefly Oscillator, same trigger)
to accept all 4 target symbols in a single reframing pass. Confirms the
"bounded-oscillator-as-continuous-sizing-dial" pattern continues to
generalize well across asset classes once the crypto leverage-cap
recalibration is applied at the retuning step rather than as a separate
follow-up iteration.

## Notes

- Formula and SuperSmoother implementation reused verbatim from the
  existing accepted knowledge base entry for the mean-reversion variant
  (no fresh web research needed this sub-step, since the construction was
  already fully disclosed and confirmed in this repo).
- Walk-forward fallback: manual 4-equal-slice split (same as other
  `run_validate_*.py` scripts, `vbt.utils.splitting.RangeSplitter`
  unavailable in the installed vectorbt version).
- Source: https://financial-hacker.com/the-inverse-fisher-transform/
