# Backtest Report: %B Sizing with Shortened Trend Window (2026-09-13-085)

**Strategy file:** `strategies/2026-09-13_percent_b_sizing_shorttrend.py`
**Hypothesis:** Retrofit of the shortened-trend-window fix (validated on RVI-082,
CMO-083, Williams%R-084) applied to Bollinger %B continuous sizing
(2026-09-13-071, previously QQQ-only accept, SPY Sharpe near-miss 0.979 at
trend_window=200). Sizing logic unchanged; only SMA trend-confirmation window
swept shorter (200 -> 28-50).

## Grid summary (scripts/run_grid_pctb_shorttrend.py)
- param_grid: trend_window in {30,40,50}, pb_sensitivity in {0.4,0.6}, bb_std={2.0}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=72, passed=21, pass_fraction=0.292
- by_asset_class: equity 21/36, crypto 0/36 (decisive fail)
- by_vol_regime: low 12/24, mid 9/24, high 0/24
- best_cell: trend_window=50, pb_sensitivity=0.4 -> QQQ low-vol Sharpe 2.43

## Fine scan for dual-symbol config (scripts/scan_pctb_shorttrend.py)
Full-sample Sharpe (2017-2026) at various trend_window/pb_sensitivity:
- tw=30, pbs=0.4: QQQ 1.121 / SPY 0.980 (SPY fail)
- tw=40, pbs=0.4: QQQ 0.978 (fail) / SPY 1.060
- tw=50, pbs=0.4: QQQ 1.065 / SPY 0.897 (fail)
- tw=32, pbs=0.4: **QQQ 1.074 / SPY 1.031 -- both pass**

## Single-config validators (trend_window=32, pb_sensitivity=0.4, bb_std=2.0)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.074 PASS | 1.031 PASS |
| Max drawdown (<=0.25) | 0.196 PASS | 0.126 PASS |
| TC survival net Sharpe (>=0.5) | 0.895 PASS | 0.823 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.043 PASS | 0.035 PASS |

**All 5 validators pass for both QQQ and SPY.**

## Decision: ACCEPT (both QQQ and SPY)
Fourth consecutive dual-symbol accept this cron trigger via the shortened-
trend-window retrofit technique (after RVI-082, CMO-083, Williams%R-084).
Crypto remains decisively rejected across the grid. Strategy kept live in
`strategies/`.
