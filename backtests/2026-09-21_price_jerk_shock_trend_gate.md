# 2026-09-21 Price Jerk Shock (3rd derivative), Trend-Gated

**Hypothesis:** Sudden upward "jerk" (3rd derivative of EMA-smoothed log
price, i.e. rate of change of price acceleration) that is statistically
extreme (z-score of rolling jerk >= 2) predicts a short-term continuation
move when the market is already in an uptrend (close > 200d SMA), since the
source material frames "shock" jerk readings as early signals of
breakout/reversal that need a trend filter to be tradeable.

**Source:** https://www.tradingview.com/script/eUZZ1SMw-Shock-Detector-Price-Jerk-with-Std-Dev-Bands/
("Shock Detector: Price Jerk with Std-Dev Bands", tmfou, Aug 2025) — describes
the jerk indicator and std-dev-band shock detection; the specific entry/exit
trading rule (trend-gated shock entry, hysteresis exit, max-hold) is this
iteration's own operationalization, not from the source.

**Strategy file:** `strategies/2026-09-21_price_jerk_shock_trend_gate.py`

## Step 6 — Grid test summary (shock_z: [1.5, 2.0, 2.5] x trend_window: [100, 200], SPY/QQQ/BTC/ETH, vol terciles)

- total_cells: 72, passed_cells: 13, **pass_fraction: 0.181**
- by_asset_class: equity 13/36 passed, **crypto 0/36 passed**
- by_vol_regime: low 10/24, mid 3/24, **high 0/24**
- best_cell: shock_z=2.0, trend_window=100, SPY, low-vol regime, Sharpe=2.75
- worst_cell: shock_z=2.0, trend_window=100, ETH/USDT, low-vol regime, Sharpe=-0.93

Only holds up in equity, low/mid-vol regimes; fails uniformly on crypto and
in high-vol regimes across both assets.

## Step 7 — Single-config validators (best cell: shock_z=2.0, trend_window=100, SPY, full 2019-2026 sample)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.970 | >= 1.0 |
| Max drawdown | PASS | 0.0546 | <= 0.25 |
| Transaction cost survival (10bps/trade, 66 trades) | PASS | net Sharpe 0.579 | >= 0.5 |
| Walk-forward (manual 4-split fallback; `vbt.utils.splitting.RangeSplitter` broken in this install, per repo convention) | PASS | 3/4 splits positive (0.75) | >= 0.75 |
| Parameter sensitivity (shock_z sweep 1.5/2.0/2.5) | PASS | relative std 0.123 | <= 0.5 |

Full-sample Sharpe (0.97) narrowly misses the 1.0 threshold despite the
best-cell low-vol-regime slice showing Sharpe 2.75 — the low-vol slice
Sharpe is not representative of the whole holding period once mid/high-vol
stretches are included.

## Step 8 — Decision: **REJECTED**

Primary validator (Sharpe ratio on full sample) failed (0.970 < 1.0), despite
passing MDD, cost survival, walk-forward, and parameter sensitivity. Grid
also shows the idea is narrow: only 13/72 cells passed, concentrated in
equity + low/mid-vol regimes, 0/36 on crypto. Strategy file and this report
are kept as a record per RESEARCH_LOOP.md Step 8 (rejected attempt, not a
live strategy).
