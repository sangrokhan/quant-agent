# Backtest Report: CSI (Commodity Selection Index) Trend-Strength Regime Gate

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_csi_commodity_selection_index_regime.py`
**Source:** https://www.prorealcode.com/prorealtime-indicators/wilders-csi-commodity-selection-index/,
https://forex-indicators.net/trend-indicators/commodity-selection-index
(J. Welles Wilder, "New Concepts in Technical Trading Systems")

## Hypothesis

CSI = ADXR(14) * ATRbalanced(14,3), combining trend strength with normalized
volatility into Wilder's original cross-sectional commodity-ranking score.
Time-series adaptation: use CSI's own rolling percentile rank (over a
126-day lookback) as a trend-strength+volatility regime gate for a simple
SMA(40) trend-following entry, on the theory that a favorable CSI regime
for a single asset over time mirrors Wilder's cross-sectional "which
commodity to trade" logic. First CSI strategy in this repo.

## Step 6 — Grid test summary

Grid: `csi_percentile_threshold` in {0.4, 0.5, 0.6}, `max_hold_days` in
{15, 20, 30}, symbols {QQQ, SPY, BTC/USDT, ETH/USDT}, vol_regime_splits=3
(108 cells).

- **pass_fraction: 0.370** (40/108)
- **by_asset_class:** equity 24/54; crypto 16/54 (both show some signal)
- **by_vol_regime:** low 27/36; mid 7/36; high 6/36
- **best_cell:** QQQ, low-vol, `csi_percentile_threshold=0.6, max_hold_days=15`, Sharpe 3.32
- **worst_cell:** QQQ, high-vol, same config, Sharpe -0.60

## Step 7 — Single-config validators (grid-best config)

| Symbol | Sharpe | MDD | TC-survival | Param-sensitivity |
|---|---|---|---|---|
| QQQ | **FAIL** 0.631 | PASS 0.193 | **FAIL** 0.455 | near-miss PASS 0.429 |
| SPY | **FAIL** 0.876 | PASS 0.105 | PASS 0.573 | PASS 0.236 |
| BTC/USDT | **FAIL** 0.162 | **FAIL** 0.405 | **FAIL** -0.021 | PASS 0.197 |
| ETH/USDT | **FAIL** 0.226 | **FAIL** 0.404 | **FAIL** 0.015 | PASS 0.197 |

Crypto fails badly across the board (MDD ~40%, negative net-of-cost Sharpe
from ~2970 trades over the sample due to hourly-bar re-evaluation of the
percentile-rank gate). Equity is a near-miss on Sharpe for both symbols.

Walk-forward skipped for all symbols (pre-existing tooling bug).

## Step 8 — Decision: REJECT (all 4 symbols)

Despite a strong grid pass_fraction (0.370) with genuine regime-slice
signal on both asset classes, full-sample Sharpe fails everywhere. Crypto
additionally fails decisively on MDD and TC-survival. This confirms the
cross-sectional-to-time-series adaptation of CSI does not by itself
overcome regime concentration; a future iteration could explore combining
the CSI regime gate with the already-accepted ADXR continuous-sizing dial
(2026-09-16-054) rather than a discrete percentile-rank threshold.
