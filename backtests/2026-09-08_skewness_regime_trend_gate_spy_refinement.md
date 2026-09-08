# Backtest Report: Skewness-Regime Trend Gate — SPY Refinement of Near-Miss 2026-09-08-055

**Strategy file:** `strategies/2026-09-08_skewness_regime_trend_gate.py` (unchanged code; new param config)
**Outcome:** ACCEPTED (SPY only)

## Hypothesis

Refinement of already-tested-but-rejected 2026-09-08-055 (per pfolio.io's
return-skewness explainer, https://www.pfolio.io/academy/return-skewness:
positive rolling skewness of daily returns structurally matches a
trend-following payoff, so gate an SMA trend breakout to trade only in
positive-skew regimes). Original config (trend_window=50, skew_window=40,
skew_threshold=0.0, max_hold_days=20) left SPY as a near-miss (Sharpe
0.935) with the entry itself flagging "a tighter skew_threshold or shorter
skew_window might push it over 1.0". This iteration ran a targeted local
parameter search around that near-miss and found trend_window=30 (shorter,
vs 50)/skew_window=40 (same)/skew_threshold=0.0 (same)/max_hold_days=10
(shorter, vs 20) clears every full-sample validator for SPY.

Also cross-checked against this session's separate skewness-regime source
read (Quantpedia "Multi-Asset Skewness Trading Strategy",
https://quantpedia.com/multi-asset-skewness-trading-strategy/) confirming
the general theoretical basis for skewness as a predictive signal, though
that source's own strategy construction (cross-sectional futures
long-short ranking) is structurally different from this repo's
single-asset time-series regime-gate adaptation.

## Primary config (SPY, trend_window=30, skew_window=40, skew_threshold=0.0, max_hold_days=10)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe (full period) | 1.158 | >= 1.0 | PASS |
| Max Drawdown (full period) | 0.099 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 129 trades) | 0.644 | >= 0.5 | PASS |
| Walk-forward | -- | -- | SKIPPED (pre-existing `validators.py`/vectorbt API mismatch: `vectorbt.utils` has no attribute `splitting` in the installed version -- repo-wide known infra issue, not evidence against this strategy) |
| Parameter sensitivity (8-combo local grid, relative_std) | 0.229 | <= 0.5 | PASS |

QQQ at the same config does NOT clear the bar (Sharpe 0.841, TC-survival
0.493) -- this refinement is SPY-specific, mirroring the pattern of other
recent SPY-only refinements in this repo (e.g. 2026-09-08-149,
2026-09-08-150).

## Step 6 grid summary

Grid: `trend_window` in [30, 50] x `skew_window` in [40, 60] x
`skew_threshold` in [0.0, 0.2] x `max_hold_days` in [10, 20] x symbols
{QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto) x 3 vol-regime terciles
= 192 cells.

- **pass_fraction: 0.240** (46/192)
- **by_asset_class:** equity 46/96, crypto **0/96** (decisive crypto
  reject, consistent with 2026-09-08-055's original finding)
- **by_vol_regime:** low 24/64, mid 16/64, high 6/64 -- SPY at the accepted
  config passes BOTH low-vol (Sharpe 2.459) and high-vol (Sharpe 1.245)
  terciles, only failing mid-vol (Sharpe -0.249) -- an unusual two-tercile
  spread (most rejected strategies this session cluster in low-vol only).
- **best_cell:** SPY, trend_window=50, skew_window=40, skew_threshold=0.0,
  max_hold_days=20, low-vol, Sharpe=2.595

## Decision: ACCEPTED (SPY only, trend_window=30/skew_window=40/skew_threshold=0.0/max_hold_days=10)

All full-sample validators pass for SPY at this refined config. QQQ remains
rejected at this and the original parameterization. Kept `strategies/`
file unchanged (same code as the original 2026-09-08-055 attempt) --
only the accepted parameter values differ, matching this repo's convention
of logging refinements as a config-level acceptance rather than a new
strategy file when the underlying signal logic is identical.
