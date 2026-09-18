# Backtest Report: Lower Highs/Lower Lows 3-Day Reversal — Low-Vol Regime-Gated Rescue (QQQ, max_hold_days=10, vol_regime_ratio=1.0)

**Date:** 2026-09-18
**Status:** REJECTED (rescue attempt failed, worse than ungated)

## Hypothesis

Direct rescue of this same cron trigger's prior rejection 2026-09-18-093
(Lower Highs/Lower Lows 3-Day Reversal, ungated: QQQ full-sample Sharpe
0.66/param sensitivity 0.532 both marginally failed, isolated low-vol
tercile Sharpe 1.80). This variant adds the same low-vol realized-vol
regime gate used successfully in the 123-pattern rescue (2026-09-18-091).

## Step 6 grid summary (`grid_result_lower_highs_lower_lows_3day_volgate.json`)

- param_grid: `max_hold_days` in [5, 10], `vol_regime_ratio` in [0.8, 1.0]
- symbols: equity (QQQ, SPY), crypto (BTC/USDT, ETH/USDT)
- vol_regime_splits: 3
- **pass_fraction: 0.125 (6/48 cells)**
- by_asset_class: equity 6/24, crypto 0/24
- by_vol_regime: low 6/16, mid 0/16, high 0/16
- best_cell: QQQ, max_hold_days=10, vol_regime_ratio=1.0, low-vol regime, Sharpe 1.72

## Step 7 single-config validation (QQQ, max_hold_days=10, vol_regime_ratio=1.0, full sample 2015-01-01 to 2026-09-01)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.372 | >= 1.0 |
| Max drawdown | pass | 0.140 | <= 0.25 |
| TC survival (10bps/trade, 39 trades) | **FAIL** | net Sharpe 0.305 | >= 0.5 |
| Walk-forward (4 splits) | pass (borderline) | 0.75 pass fraction | >= 0.75 |
| Parameter sensitivity (4-combo grid) | **FAIL** | rel_std 2.438 | <= 0.5 |

## Decision: REJECT

Unlike the 123-pattern rescue (which improved full-sample Sharpe 0.79 ->
1.29), gating the lower-highs/lower-lows pattern by low-vol regime made
things WORSE on the full-sample metric (Sharpe dropped 0.66 -> 0.37,
TC-survival flipped from pass to fail) despite the grid's isolated
low-vol-tercile cell still showing a healthy 1.72. This is likely because
the gate cuts trade count roughly in half (81 trades ungated -> 39 gated)
concentrated into fewer, thinner low-vol windows, and the full-sample
return series (with long stretches flat outside the low-vol regime) has
much higher relative variance -- param sensitivity across the 4-combo grid
exploded to 2.44. The rescue technique that worked for the 123-pattern
does not generalize to this pattern; reject outright rather than pursue
further retuning this iteration.

Left `strategies/2026-09-18_lower_highs_lower_lows_3day_volgate.py` in
place as a record of a failed rescue attempt.
