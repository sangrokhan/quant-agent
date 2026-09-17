# Backtest Report: VIX9D:VIX Smoothed-Gate Trend (SPY rescue) (2026-09-18)

## Hypothesis
Direct fix attempt for prior id 2026-09-10-038 (VIX9D:VIX ratio gate + SMA
trend-following, near-missed on both QQQ (Sharpe 0.909) and SPY (Sharpe
0.905), notes attributing the shortfall to raw-ratio whipsaw turnover).
This iteration applies a rolling-mean smoothing to the VIX9D/VIX ratio
before gating (same smoothing technique already validated in
strategies/2026-09-06_vix_term_structure_relief.py), keeping the identical
underlying VIX9D-reacts-faster-than-VIX signal and SMA(trend_window) trend
filter.

## Parameter Scan (2019-01-01 to 2026-09-01, limited by ^VIX9D data availability)
Scan: trend_window in {50,100} x vix_ratio_threshold in {0.95,1.0,1.05} x
vix_smooth_window in {3,5,10}, QQQ and SPY.

Top SPY configs: (trend_window=50, threshold=1.05, smooth=3): Sharpe 1.017;
(100, 1.0, 10): Sharpe 1.003; (50, 1.0, 10): Sharpe 0.998.
Top QQQ configs: (50, 1.05, 10): Sharpe 0.988 (still a near-miss, improved
from the parent's 0.909 but not clearing 1.0).

## Single-Config Validator Results (Step 7)

### SPY, trend_window=50, vix_ratio_threshold=1.05, vix_smooth_window=3
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.017 | >= 1.0 | YES |
| Max drawdown | 0.188 | <= 0.25 | YES |
| Net Sharpe after costs (10bps/trade, 129 trades) | 0.752 | >= 0.5 | YES |
| Walk-forward (4 splits) | 1.0 pass fraction | >= 0.75 | YES |
| Parameter sensitivity (9-cell sweep, relative std) | 0.168 | <= 0.5 | YES |

**All 5 validators pass -- ACCEPTED for SPY.**

### QQQ
Best found config (trend_window=50, threshold=1.05, smooth=10) reaches
Sharpe 0.988 -- still a near-miss (though improved from the parent's
0.909). Not pursued further to single-config validators this iteration;
QQQ remains rejected pending a future retune.

## Decision
**ACCEPT for SPY** (strategies/2026-09-18_vix9d_vix_smoothed_gate_trend.py,
trend_window=50, vix_ratio_threshold=1.05, vix_smooth_window=3). QQQ
remains a near-miss (Sharpe 0.988), flagged for a possible future retune.
Rescues the parent 2026-09-10-038's SPY near-miss (0.905 -> 1.017) via
smoothing alone, no architectural change.
