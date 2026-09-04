# Backtest Report: VHF Regime-Gated Trend Following (2026-09-04)

**Hypothesis:** VHF (Adam White) measures trend efficiency: VHF_n =
(max(close,n) - min(close,n)) / sum(|close.diff()|, n). A high/rising VHF
confirms price is moving efficiently in one direction. Per
trendsandbreakouts.com's guide, VHF should pair with a directional signal
(here, close vs. a medium-term SMA) since VHF alone has no direction. This
strategy: long entry when close is above the SMA AND VHF is above a
threshold AND rising; exit when close drops below the SMA, VHF falls below
the threshold, or a max_hold_days time-stop. Source:
https://trendsandbreakouts.com/vertical-horizontal-filter. First VHF
strategy in this repo -- distinct from ADX (already tested/rejected
several times, different formula basis: directional movement +DI/-DI vs.
VHF's raw close range over cumulative path).

**Strategy file:** `strategies/2026-09-04_vhf_regime_trend_following.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: vhf_window[18,28], vhf_threshold[0.30,0.40], sma_window[50,100];
symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 64, passed_cells: 12, pass_fraction: 0.188
by_asset_class: equity 12/48, crypto 0/16
by_vol_regime: low 12/16, mid 0/16, high 0/16
best_cell: QQQ, low-vol, vhf_window=28/vhf_threshold=0.3/sma_window=100 -> Sharpe 2.455
worst_cell: QQQ, high-vol, vhf_window=28/vhf_threshold=0.4/sma_window=50 -> Sharpe -1.266
```

## Step 7 single-config validators (vhf_window=28, vhf_threshold=0.30, sma_window=100, max_hold_days=30, full sample 2018-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ 0.721 (141 trades) | ❌ 0.733 (173 trades) | 1.0 |
| Max drawdown | ✅ 0.171 | ✅ 0.116 | 0.25 |
| Transaction cost survival (10bps/trade) | ✅ 0.506 (barely) | ❌ 0.357 | 0.5 |
| Walk-forward | ⚠️ skipped (full-sample already fails) | ⚠️ skipped | 0.75 |
| Parameter sensitivity (grid pass_fraction) | ❌ 18.8% pass rate across grid | -- | 0.5 |

## Verdict: **REJECTED**

Grid pass_fraction 18.8% (12/64) is entirely a low-vol-regime artifact
(12/16 low vs 0/16 mid, 0/16 high) and 0/16 on crypto. Full-sample Sharpe
confirmation fails on both QQQ (0.721) and SPY (0.733) at the best grid
config -- the edge doesn't survive out of the narrow low-vol slice. Not
accepted even as a narrow-scope strategy since the primary-config
full-sample check misses the bar on both equity symbols.
