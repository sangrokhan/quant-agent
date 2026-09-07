# Detrended Price Oscillator (DPO) Cyclical-Low + EMA Trend Filter — QQQ (equity-only)

**Strategy file:** `strategies/2026-09-08_dpo_cyclelow_trend_filter.py`
**Source(s):** https://arrowalgo.com/detrended-price-oscillator-dpo-complete-guide-algorithmic-trading/
**Knowledge base id:** 2026-09-08-049

## Hypothesis

DPO(t) = Close[t - (period/2+1)] - SMA(period, t) removes trend, exposing
short-term cycle position. Per the source's explicit prescription ("DPO
without a trend filter is a coin flip"), combine a DPO cyclical-low reading
(bottom decile of rolling DPO distribution) with a trend filter (price above
a 50-EMA) as the entry condition, exiting when DPO reaches a cyclical high
or the trend filter flips. First DPO-based construction in this repo.

## Best config (from grid search)

`dpo_period=20, dpo_low_quantile=0.1, trend_ema_window=50` (dpo_lookback=126, dpo_high_quantile=0.9, max_hold_days=20 — defaults)

## Step 6 grid summary (dpo_period x dpo_low_quantile x trend_ema_window, 2 assets x 3 vol regimes)

- total_cells: 96, passed_cells: 25, pass_fraction: 0.260
- by_asset_class: equity 25/48 passed, **crypto 0/48 passed**
- by_vol_regime: low 16/32, mid 9/32, high 0/32
- best_cell: dpo_period=20, dpo_low_quantile=0.1, trend_ema_window=50, QQQ, low-vol, Sharpe 2.918
- worst_cell: same params, QQQ, high-vol regime, Sharpe -0.495

Same clean pattern seen elsewhere in this repo: works only on equity indices,
fails uniformly on crypto, concentrated in low/mid vol regimes, fails
entirely in high-vol.

## Step 7 full-sample validators (best config, 2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-fwd pass frac | Param sensitivity (rel std) | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.025 (pass, thr 1.0) | 0.168 (pass, thr 0.25) | 0.923 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.129 (pass, thr 0.5) | **ALL PASS** |
| SPY | 0.668 (**fail**, thr 1.0) | 0.161 (pass, thr 0.25) | 0.522 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.178 (pass, thr 0.5) | FAIL (Sharpe only) |

## Decision: ACCEPT (QQQ-only, equity-only scope)

QQQ passes every validator run (Sharpe 1.025 just clears the 1.0 bar, all
other metrics comfortably pass, only 62 trades over 8.7yr, low turnover).
SPY fails only the Sharpe threshold (0.668 vs 1.0) but otherwise looks
healthy (passes TC survival, walk-forward, param sensitivity) — closer to a
near-miss than a decisive rejection, worth flagging for a future
volatility-regime-gate follow-up given the by_vol_regime concentration
pattern (16 low + 9 mid, 0 high). Crypto rejected outright (0/48 grid
cells). Accepted narrowly scoped to QQQ only.
