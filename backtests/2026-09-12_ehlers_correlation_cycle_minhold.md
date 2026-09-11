# Ehlers Correlation Cycle — Min-Hold Fix — REJECTED (walk-forward fail)

**Strategy file:** `strategies/2026-09-12_ehlers_correlation_cycle_minhold.py`
**Source:** Direct fix attempt for near-miss `2026-09-12-138` (Ehlers
Correlation Cycle / Market State phasor regime-switch,
https://www.mesasoftware.com/papers/CORRELATION%20AS%20A%20CYCLE%20INDICATOR.pdf).
That report's own notes suggested "adding a minimum-hold-period filter to
reduce whipsaw" as a next step — implemented here.

## Hypothesis

Same Correlation-Cycle/Angle/State math as 2026-09-12-138 (unchanged), but
a `min_hold_days`-bar hysteresis is applied to the raw target position to
suppress rapid flip-flopping around the 9-degree flatline threshold, aiming
to cut trade count/transaction-cost drag without materially altering signal
quality.

## Grid test summary (Step 6)

- Grid: `period` in [14, 20, 30] x `min_hold_days` in [3, 5, 8]; symbols
  QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3. 108
  total cells.
- **pass_fraction: 0.194 (21/108)**
- by_asset_class: equity 21/54 passed; **crypto 0/54 (decisive fail)**
- by_vol_regime: low 15/36, mid 6/36, **high 0/36 (decisive fail)**
- best_cell: period=30, min_hold_days=5, SPY, low-vol, Sharpe 2.638

## Single-config validation (Step 7) — period=20, min_hold_days=3, full sample 2019-2026

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.906 ❌ | 1.083 ✅ | ≥ 1.0 |
| Max drawdown | 0.247 ✅ | 0.144 ✅ | ≤ 0.25 |
| TC survival (10bps/trade, 214/220 trades) | 0.635 ✅ | 0.693 ✅ | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-slice) | 0.25 ❌ (1/4) | 0.50 ❌ (2/4) | ≥ 0.75 |
| Parameter sensitivity (period x min_hold grid, 9 combos) | 0.445 ✅ | 0.496 ✅ | ≤ 0.5 relative std |

(`validation/validators.py::check_walk_forward` currently raises
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` in
this environment's installed vectorbt version — worked around with a manual
4-equal-chunk walk-forward split, same workaround pattern as
2026-09-12-138's report.)

## Decision: REJECTED

The min-hold fix did cut trade count modestly (214-220 vs. the original
246-258) and pushed SPY's full-sample Sharpe over the 1.0 threshold (1.083
vs. 0.926 before), confirming the whipsaw-reduction hypothesis has some
truth to it. However QQQ's Sharpe still falls short (0.906), and critically
**both symbols now fail walk-forward robustness** (QQQ 1/4, SPY 2/4 splits
positive-Sharpe, vs. the pre-fix version's 3/4 and 4/4) — the min-hold
filter appears to concentrate the strategy's edge into fewer, larger
sub-periods rather than distributing it consistently across time, making
it less robust out-of-sample despite the improved full-sample headline
number. Crypto remains decisively rejected (0/54) and high-vol regime
remains a decisive fail (0/36), both unchanged from the pre-fix version.
Net: not accepted. A future iteration could try a smaller min_hold_days
grid centered near the original (no min-hold) baseline, or a different
whipsaw-reduction mechanism (e.g. requiring 2 consecutive bars of the same
raw_target signal before flipping, rather than a fixed time-based lockout)
that doesn't concentrate edge into fewer discrete regimes.
