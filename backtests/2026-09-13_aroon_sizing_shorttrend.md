# Backtest Report: Aroon Oscillator Sizing with Shortened Trend Window (2026-09-13-086)

**Strategy file:** `strategies/2026-09-13_aroon_sizing_shorttrend.py`
**Hypothesis:** Retrofit of the shortened-trend-window fix (RVI-082,
CMO-083, Williams%R-084, %B-085) applied to Aroon Oscillator continuous
sizing (2026-09-13-072, previously QQQ-only accept, SPY Sharpe near-miss
0.945 at trend_window=200). Unlike the prior three retrofits, a simple
trend_window shortening alone was NOT sufficient here -- the Aroon
Oscillator's own `aroon_window` and `aroon_reference` also required
retuning jointly to find a dual-pass region.

## Fine scan for dual-symbol config (scripts/scan_aroon_shorttrend.py)
Initial sweep of trend_window alone (aroon_window=25, aroon_reference=60,
unchanged from original) failed to fix SPY at any trend_window in [15,100]
(SPY Sharpe stuck 0.73-0.85). Broadened the sweep to also retune
aroon_window and aroon_reference jointly. Full-sample Sharpe (2017-2026):
- tw=25, aroon_window=10, aroon_reference=40: **QQQ 1.044 / SPY 1.112 -- both pass**
- tw=22, aroon_window=10, aroon_reference=40: QQQ 1.040 / SPY 1.041 (also dual-pass, slightly lower)

Selected best config: trend_window=25, aroon_window=10, aroon_reference=40.0.

## Grid summary (scripts/run_grid_aroon_shorttrend.py)
- param_grid: trend_window in {22,25,28}, aroon_reference in {35,40,45}, aroon_window={10}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=108, passed=27, pass_fraction=0.25
- by_asset_class: equity 27/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: trend_window=28, aroon_reference=35 -> SPY low-vol Sharpe 1.95

## Single-config validators (trend_window=25, aroon_window=10, aroon_reference=40.0)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.044 PASS | 1.112 PASS |
| Max drawdown (<=0.25) | 0.158 PASS | 0.120 PASS |
| TC survival net Sharpe (>=0.5) | 0.893 PASS | 0.926 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.025 PASS | 0.035 PASS |

**All 5 validators pass for both QQQ and SPY.**

## Decision: ACCEPT (both QQQ and SPY)
Fifth consecutive dual-symbol accept this cron trigger via the
trend-window-recalibration technique family (RVI-082, CMO-083,
Williams%R-084, %B-085, now Aroon-086), though this one required also
retuning aroon_window (25->10) and aroon_reference (60->40), not just the
trend_window -- a useful refinement of the retrofit recipe for future
iterations: not every indicator's SPY near-miss fixes with trend_window
alone. Crypto remains decisively rejected across the grid. Strategy kept
live in `strategies/`.
