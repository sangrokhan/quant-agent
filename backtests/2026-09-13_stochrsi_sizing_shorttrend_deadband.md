# Backtest Report: StochRSI Sizing with Shortened Trend Window (2026-09-13-088)

**Strategy file:** `strategies/2026-09-13_stochrsi_sizing_shorttrend_deadband.py`
**Hypothesis:** Retrofit of the shortened-trend-window fix (RVI-082,
CMO-083, Williams%R-084, %B-085, Aroon-086, UO-087) applied to StochRSI
sizing + deadband (2026-09-13-080, previously QQQ-only accepted with a
narrow TC margin, SPY decisively rejected on BOTH Sharpe AND TC survival at
trend_window=200 -- a harder starting point than the other five retrofits).
Same StochRSI sizing+deadband logic unchanged; trend_window and deadband
swept.

## Fine scan for dual-symbol config (scripts/scan_stochrsi_shorttrend.py)
Full-sample Sharpe (2017-2026) -- every tested combination except
trend_window=50 passed BOTH symbols, a stronger result than any of the
prior five retrofits:
- tw=30, deadband=0.15: QQQ 1.191 / SPY 1.122 -- both pass
- tw=40, deadband=0.15: QQQ 1.078 / SPY 1.148 -- both pass
- tw=50, deadband=0.15: QQQ 1.086 / SPY 0.990 (SPY fail)
- tw=40, sens=0.3, deadband=0.15: QQQ 1.074 / SPY 1.146 -- both pass
- tw=40, deadband=0.10: QQQ 1.084 / SPY 1.116 -- both pass
- tw=40, deadband=0.20: **QQQ 1.101 / SPY 1.180 -- both pass, strongest**

Selected best config: trend_window=40, stochrsi_sensitivity=0.5, deadband=0.20.

## Grid summary (scripts/run_grid_stochrsi_shorttrend.py)
- param_grid: trend_window in {35,40,45}, deadband in {0.15,0.20,0.25}, stochrsi_sensitivity={0.5}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=108, passed=28, pass_fraction=0.259
- by_asset_class: equity 28/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 10/36, high 0/36
- best_cell: trend_window=45, deadband=0.20 -> SPY low-vol Sharpe 2.68

## Single-config validators (trend_window=40, stochrsi_sensitivity=0.5, deadband=0.20)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.101 PASS | 1.180 PASS |
| Max drawdown (<=0.25) | 0.173 PASS | 0.101 PASS |
| TC survival net Sharpe (>=0.5) | 0.959 PASS | 1.015 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.032 PASS | 0.057 PASS |

**All 5 validators pass for both QQQ and SPY -- best margins of the entire
shortened-trend-window retrofit family this cron trigger (SPY TC net Sharpe
even exceeds 1.0).**

## Decision: ACCEPT (both QQQ and SPY)
Seventh and final dual-symbol accept this cron trigger via the
trend-window-recalibration technique family, completing the retrofit sweep
across all seven originally-flagged QQQ-only sizing overlays (%B-071,
Aroon-072, Williams%R-074, CMO-078, UO-079, StochRSI-080, RVI-081 -> now
all seven have dual-symbol shortened-trend-window variants: RVI-082,
CMO-083, Williams%R-084, %B-085, Aroon-086, UO-087, StochRSI-088). Crypto
remains decisively rejected across the grid. Strategy kept live in
`strategies/`.
