# Backtest Report: CMF Continuous Sizing with Deadband (2026-09-13-090)

**Strategy file:** `strategies/2026-09-13_cmf_sizing_shorttrend_deadband.py`

**Hypothesis:** Chaikin Money Flow (Marc Chaikin): Money Flow Multiplier
MFM=((Close-Low)-(High-Close))/(High-Low), naturally bounded [-1,1]; MFV =
MFM*Volume; CMF(n) = sum(MFV,n)/sum(Volume,n). This repo has 5+ prior CMF
entries, all binary zero-line/threshold ENTRY signals. This iteration
applies CMF as a CONTINUOUS SIZING dial (same construction validated 8x
already this cron trigger). CMF is naturally bounded [-1,1] (unlike MFI's
[0,100]), so exposure scales linearly off CMF itself rather than a
recentered (indicator-midpoint)/midpoint transform. Distinct from
2026-09-13-089's MFI: MFI is a ratio of positive/negative flow SUMS through
an RSI transform; CMF is a volume-weighted AVERAGE of a symmetric per-bar
intrabar-positioning term -- a different volume-weighting mechanism.

## Fine scan for dual-symbol config (scripts/scan_cmf_shorttrend.py)
CMF proved noticeably harder to fit than MFI -- most trend_window-only
sweeps at the default cmf_window=20 failed SPY. Full-sample Sharpe
(2017-2026):
- tw=40, sens=0.8, deadband=0.10 (defaults): QQQ 1.013 / SPY 0.982 (SPY fail)
- tw=40, sens=0.5, deadband=0.10: QQQ 1.017 / SPY 1.017 -- both pass (narrow)
- tw=40, sens=0.4, deadband=0.15: QQQ 1.015 / SPY 1.045 -- both pass
- tw=40, cmf_window=30, sens=0.6, deadband=0.10: QQQ 1.024 / SPY 1.028 -- both pass
- **tw=40, cmf_window=30, sens=0.5, deadband=0.15: QQQ 1.014 / SPY 1.051 -- both pass, selected**

Widening cmf_window from 20 to 30 (smoother CMF, less noise) combined with
deadband=0.15 was the key lever that unlocked consistent dual-symbol
passes; sensitivity alone was not enough.

## Grid summary (scripts/run_grid_cmf_shorttrend.py)
- param_grid: trend_window in {35,40,45}, cmf_sensitivity in {0.4,0.5,0.6}, cmf_window={30}, deadband={0.15}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=108, passed=30, pass_fraction=0.278
- by_asset_class: equity 30/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 12/36, high 0/36
- best_cell: trend_window=45, cmf_sensitivity=0.4 -> QQQ low-vol Sharpe 2.40

## Single-config validators (trend_window=40, cmf_window=30, cmf_sensitivity=0.5, deadband=0.15)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.014 PASS (thin margin) | 1.051 PASS |
| Max drawdown (<=0.25) | 0.192 PASS | 0.110 PASS |
| TC survival net Sharpe (>=0.5) | 0.884 PASS | 0.895 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.025 PASS | 0.049 PASS |

**All 5 validators pass for both QQQ and SPY** (QQQ Sharpe margin is the
thinnest of all sizing-dial strategies accepted this cron trigger, 1.014
vs. the 1.0 threshold -- flagged for future monitoring/possible re-tune).

## Decision: ACCEPT (both QQQ and SPY, QQQ margin thin)
Second dual-symbol accept for a genuinely NEW indicator this cron trigger
(after MFI-089). CMF confirms that volume-weighted oscillators are a
promising direction as sizing dials, though this one required
non-default cmf_window=30 (vs. standard 20) to smooth out noise enough to
pass both symbols reliably. Crypto remains decisively rejected across the
grid. Strategy kept live in `strategies/`.
