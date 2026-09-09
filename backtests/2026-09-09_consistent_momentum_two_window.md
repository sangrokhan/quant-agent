# Backtest report: Consistent Momentum (two-window consistency)

**Strategy file:** `strategies/2026-09-09_consistent_momentum_two_window.py`
**Knowledge base id:** 2026-09-09-107
**Outcome:** REJECTED

## Hypothesis

Per Quantpedia's "Consistent Momentum Strategy": only ~60% of winner/loser
stocks are "consistent" (positive momentum in both the formation window
and the following window); consistent winners significantly outperform
inconsistent winners post-formation. Adapted from the source's
cross-sectional decile-sort design to a single-asset time-series analog:
long only when both the trailing `lookback_days` return and the trailing
return over the prior non-overlapping window of the same length are
positive.

## Grid test summary (Step 6)

- Grid: `lookback_days` in [10, 21, 42, 63] x {QQQ, SPY, BTC/USDT,
  ETH/USDT} x 3 vol terciles = 48 cells.
- `pass_fraction`: **0.229** (11/48)
- `by_asset_class`: equity 11/24, crypto 0/24
- `by_vol_regime`: low 8/16, mid 3/16, high 0/16
- Best cell: SPY, low-vol tercile, `lookback_days=21`, Sharpe 2.282

## Single-config validation (Step 7), best grid config (lookback_days=21)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe, 10bps/trade) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| SPY | 0.602 (fail) | 0.165 (pass) | 0.201 (fail) | 0.75 pass | 0.133 pass |
| QQQ | 0.575 (fail) | 0.337 (fail) | 0.291 (fail) | 0.75 pass | 0.252 pass |

(Walk-forward computed via a manual 4-split implementation since
`validation/validators.py::check_walk_forward` errors against the
installed vectorbt version -- `vectorbt.utils` has no `splitting`
attribute. This is a pre-existing repo/environment issue, not specific to
this strategy.)

## Verdict

Grid pass_fraction looked promising (0.229, concentrated in equity
low/mid-vol) but full-sample Sharpe fails decisively on both symbols, and
transaction-cost survival fails hard (193/178 trades over the sample --
the daily-rebalanced approximation churns far more than the source's
intended 6-month-formation, low-turnover design). Walk-forward and
parameter-sensitivity both pass cleanly, so the underlying signal is
directionally real and stable -- turnover/cost mismatch, not signal
quality, is the failure mode. Not accepted.

**Notes for future loops:** lengthen `lookback_days` toward the source's
true ~126-day (6-month) formation window and add a `min_hold_days` gate
to cut turnover before re-testing TC-survival.
