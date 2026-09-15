# Backtest Report: TTM Scalper + inverse-vol sizing overlay, SPY rescue attempt

**Strategy file:** `strategies/2026-09-16_ttm_scalper_voltarget_buffer.py`
**Date:** 2026-09-16
**Prior id:** this cron trigger's own 2026-09-16-135 (SPY double near-miss)

## Hypothesis
Direct fix attempt for prior id 2026-09-16-135 (TTM Scalper reversal-
confirmation: SPY double near-miss Sharpe 0.866/MDD 0.261). Applies this
repo's already-validated inverse-volatility position-sizing overlay with a
no-trade rebalance buffer (construction unchanged from 2026-09-07-026) to
the unchanged TTM Scalper base signal for SPY only.

## Search result
A dedicated parameter sweep (`target_vol` in [0.08,0.10,0.12,0.15,0.18] x
`vol_cap` in [0.4,0.5,0.6,0.7,0.8,1.0] x `rebalance_buffer` in
[0.05,0.10,0.15,0.2], 120 combos) found the vol-targeting overlay DOES fix
MDD (best config's MDD 0.117, well under 0.25) but caps Sharpe at 0.972 --
still just short of the 1.0 threshold at every combination tried. The
sizing overlay improves risk-adjusted smoothness but cannot manufacture
additional raw signal quality; the underlying TTM Scalper signal on SPY
simply doesn't generate enough edge to clear Sharpe 1.0 regardless of
position sizing.

## Decision
**Reject** (SPY rescue attempt unsuccessful). SPY remains rejected per the
original 2026-09-16-135 entry. This confirms that the base-signal
near-miss on SPY was a signal-quality issue (not primarily a risk-control
issue, despite MDD also having near-missed) -- unlike the several
successful vol-targeting rescues this cron trigger where Sharpe already
comfortably cleared 1.0 and only MDD needed fixing.
