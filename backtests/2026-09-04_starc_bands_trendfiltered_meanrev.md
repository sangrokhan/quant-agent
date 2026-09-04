# Backtest Report: STARC Bands Trend-Filtered Mean Reversion (2026-09-04)

**Hypothesis:** STARC bands (SMA +/- multiplier*ATR envelope, Manning
Stoller) provide dynamic support/resistance; per Synapse Trading's
explainer, buying near the lower band works best during an overall uptrend
(source explicitly warns against symmetric use in downtrends due to
band-walking). This strategy: long entry when close crosses below the
lower STARC band AND price is above a longer-term trend SMA; exit on
crossing back above the basis SMA or upper band, trend filter breaking, or
a max_hold_days time-stop. Source:
https://synapsetrading.com/stoller-average-range-channel-starc-bands/.
First STARC strategy in this repo -- distinct from Bollinger Bands
(std-based) and Keltner Channel (EMA+ATR based) already tested.

**Strategy file:** `strategies/2026-09-04_starc_bands_trendfiltered_meanrev.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: sma_window[5,6,8], atr_mult[1.5,2.0,2.5], trend_window[50,100];
symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 144, passed_cells: 28, pass_fraction: 0.194
by_asset_class: equity 28/108, crypto 0/36
by_vol_regime: low 19/36, mid 5/36, high 4/36
best_cell: SPY, low-vol, sma_window=6/atr_mult=1.5/trend_window=100 -> Sharpe 2.252
worst_cell: QQQ, high-vol, sma_window=8/atr_mult=1.5/trend_window=50 -> Sharpe -0.652
```

## Step 7 single-config validators (sma_window=6, atr_mult=1.5, trend_window=100, max_hold_days=10, full sample 2018-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ 0.171 (54 trades) | ❌ 0.881 (66 trades) | 1.0 |
| Max drawdown | ✅ 0.149 | ✅ 0.047 | 0.25 |
| Transaction cost survival (10bps/trade) | ❌ 0.030 | ✅ 0.564 | 0.5 |
| Walk-forward | ⚠️ skipped (full-sample already fails on both symbols) | ⚠️ skipped | 0.75 |
| Parameter sensitivity (grid pass_fraction) | ❌ 19.4% pass rate across grid | -- | 0.5 |

## Verdict: **REJECTED**

Grid pass_fraction of 19.4% is dominated by low-vol regime cells only
(19/36 low-vol vs 5/36 mid, 4/36 high) and fails completely on crypto
(0/36). Full-sample Sharpe confirmation fails on both QQQ (0.171) and SPY
(0.881, just under the 1.0 bar) at the best grid config -- the edge doesn't
survive out of the narrow low-vol slice that the grid search happened to
find. Not accepted even as a narrow-scope strategy since the primary-config
full-sample check misses the bar on both equity symbols tested.
