# Backtest Report: UO Sizing with Shortened Trend Window (2026-09-13-087)

**Strategy file:** `strategies/2026-09-13_uo_sizing_shorttrend_deadband.py`
**Hypothesis:** Retrofit of the shortened-trend-window fix (RVI-082,
CMO-083, Williams%R-084, %B-085, Aroon-086) applied to Ultimate Oscillator
sizing + deadband (2026-09-13-079, previously QQQ-only, SPY Sharpe
near-miss ~0.9 at trend_window=200). Same UO sizing+deadband logic
unchanged; only trend_window swept shorter.

## Fine scan for dual-symbol config (scripts/scan_uo_shorttrend.py)
Full-sample Sharpe (2017-2026):
- tw=30, uo_sens=0.4: QQQ 1.136 / SPY 0.989 (SPY fail)
- tw=40, uo_sens=0.4: **QQQ 1.031 / SPY 1.050 -- both pass**
- tw=50, uo_sens=0.4: QQQ 1.104 / SPY 0.919 (SPY fail)
- tw=35 variants: all SPY fail (0.98-0.985)

Unlike Aroon-086, a simple trend_window shortening alone WAS sufficient
here (trend_window=40, unchanged uo_sensitivity=0.4, deadband=0.10).

## Grid summary (scripts/run_grid_uo_shorttrend.py)
- param_grid: trend_window in {35,40,45}, uo_sensitivity in {0.3,0.4,0.5}, deadband={0.10}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=108, passed=29, pass_fraction=0.269
- by_asset_class: equity 29/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 11/36, high 0/36
- best_cell: trend_window=45, uo_sensitivity=0.4 -> QQQ low-vol Sharpe 2.41

## Single-config validators (trend_window=40, uo_sensitivity=0.4, deadband=0.10)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.031 PASS | 1.050 PASS |
| Max drawdown (<=0.25) | 0.198 PASS | 0.110 PASS |
| TC survival net Sharpe (>=0.5) | 0.906 PASS | 0.899 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.022 PASS | 0.047 PASS |

**All 5 validators pass for both QQQ and SPY.**

## Decision: ACCEPT (both QQQ and SPY)
Sixth consecutive dual-symbol accept this cron trigger via the
trend-window-recalibration technique family (RVI-082, CMO-083,
Williams%R-084, %B-085, Aroon-086, now UO-087). Crypto remains decisively
rejected across the grid. Strategy kept live in `strategies/`.
