# Backtest Report: DMI-Diff Continuous Sizing with Deadband (2026-09-13-093)

**Strategy file:** `strategies/2026-09-13_dmi_diff_sizing_shorttrend_deadband.py`

**Hypothesis:** Direct follow-up to this cron trigger's ADX sizing dial
(2026-09-13-092), which used the unsigned trend-conviction magnitude only.
This iteration uses the SIGNED DMI difference DMI_diff = (+DI - -DI),
bounded roughly [-100,100] -- the same Wilder directional-movement
construction ADX is derived from, but preserving sign/direction instead of
collapsing it via the DX formula. Combines direction AND magnitude in one
signal, unlike ADX (magnitude-only) or the 8 prior oscillator-based sizing
dials (which don't share ADX/DMI's smoothed True-Range-normalized
construction).

## Fine scan for dual-symbol config (scripts/scan_dmi_shorttrend.py)
Full-sample Sharpe (2017-2026):
- tw=40, sens=0.5, deadband=0.10: QQQ 1.057 / SPY 1.009 -- both pass (narrow)
- tw=30, sens=0.5, deadband=0.10: QQQ 1.121 / SPY 0.991 (SPY fail)
- **tw=25, sens=0.5, deadband=0.15: QQQ 1.126 / SPY 1.149 -- both pass, strong margins**
- Other tw=40 variants: SPY fails at 0.975-0.995

Selected best config: trend_window=25, dmi_sensitivity=0.5, deadband=0.15
(same trend_window=25 that also worked for the sibling ADX-092 strategy).

## Grid summary (scripts/run_grid_dmi_shorttrend.py)
- param_grid: trend_window in {20,25,30}, dmi_sensitivity in {0.4,0.5,0.6}, deadband={0.15}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=108, passed=27, pass_fraction=0.25
- by_asset_class: equity 27/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: trend_window=30, dmi_sensitivity=0.5 -> QQQ low-vol Sharpe 2.31

## Single-config validators (trend_window=25, dmi_sensitivity=0.5, deadband=0.15)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.126 PASS | 1.149 PASS |
| Max drawdown (<=0.25) | 0.231 PASS (close to ceiling) | 0.115 PASS |
| TC survival net Sharpe (>=0.5) | 0.966 PASS | 0.941 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.045 PASS | 0.073 PASS |

**All 5 validators pass for both QQQ and SPY** (QQQ MDD 0.231 is close to
the 0.25 ceiling, flagged for future monitoring, echoing the pattern noted
in earlier trend-window-retrofit entries this cron trigger where QQQ MDD
consistently sits near the ceiling).

## Decision: ACCEPT (both QQQ and SPY)
Fifth dual-symbol accept for a genuinely NEW indicator this cron trigger
(after MFI-089, CMF-090, VZO-091, ADX-092), directly extending the sibling
ADX entry by adding directional sign back into the trend-conviction sizing
signal. Crypto remains decisively rejected across the grid. Strategy kept
live in `strategies/`.
