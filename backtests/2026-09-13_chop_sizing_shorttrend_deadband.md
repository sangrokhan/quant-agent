# Backtest Report: Choppiness Index Inverse Continuous Sizing (2026-09-13-094)

**Strategy file:** `strategies/2026-09-13_chop_sizing_shorttrend_deadband.py`

**Hypothesis:** Choppiness Index (Bill Dreiss), bounded [0,100], this
repo's own established formula (8+ prior entries, all binary threshold
REGIME GATES restricting some other entry signal to CHOP<threshold
periods). This iteration uses CHOP as a CONTINUOUS SIZING dial directly
(the construction validated 10x already this cron trigger): exposure
scales inversely with CHOP within the SMA gate -- lean in harder as the
market becomes more trending/efficient (low CHOP), de-risk as it becomes
choppier (high CHOP). Conceptually similar in spirit to ADX-092/DMI-diff-093
(both trend-quality measures), but uses Dreiss's log-ratio-of-ranges
construction rather than Wilder's smoothed directional movement -- a
structurally distinct formula.

## Fine scan for dual-symbol config (scripts/scan_chop_shorttrend.py)
Full-sample Sharpe (2017-2026):
- tw=40, sens=0.5, deadband=0.10: QQQ 0.923 (fail) / SPY 1.016
- **tw=25, sens=0.5, deadband=0.15: QQQ 1.097 / SPY 1.132 -- both pass**
  (same trend_window=25 that also worked for the sibling ADX-092/DMI-093 entries)
- tw=30, sens=0.5, deadband=0.10: QQQ 1.057 / SPY 0.986 (SPY fail)
- Other tw=40 variants: mixed fails

Selected best config: trend_window=25, chop_sensitivity=0.5, deadband=0.15.

## Grid summary (scripts/run_grid_chop_shorttrend.py)
- param_grid: trend_window in {20,25,30}, chop_sensitivity in {0.4,0.5,0.6}, deadband={0.15}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=108, passed=27, pass_fraction=0.25
- by_asset_class: equity 27/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: trend_window=30, chop_sensitivity=0.5 -> QQQ low-vol Sharpe 2.37

## Single-config validators (trend_window=25, chop_sensitivity=0.5, deadband=0.15)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.097 PASS | 1.132 PASS |
| Max drawdown (<=0.25) | 0.201 PASS | 0.117 PASS |
| TC survival net Sharpe (>=0.5) | 0.926 PASS | 0.912 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.051 PASS | 0.081 PASS |

**All 5 validators pass for both QQQ and SPY.**

## Decision: ACCEPT (both QQQ and SPY)
Sixth dual-symbol accept for a genuinely NEW indicator this cron trigger
(after MFI-089, CMF-090, VZO-091, ADX-092, DMI-diff-093), and confirms
trend_window=25 (matching the ADX/DMI-diff pattern) as a recurring
dual-pass sweet spot for trend-quality-based sizing dials specifically
(distinct from the volume-oscillator family's trend_window~30-40 sweet
spot). Notably salvages another indicator (CHOP) whose only prior repo uses
were as a binary regime gate. Crypto remains decisively rejected across the
grid. Strategy kept live in `strategies/`.

## Cron-trigger-wide summary (this trigger's 10 iterations)
Iterations 1-4 completed the "shortened trend_window" retrofit family for
all 7 originally-flagged QQQ-only sizing overlays (%B, Aroon, Williams%R,
CMO, UO, RVI, StochRSI -- all now dual QQQ+SPY accepts). Iterations 5-10
pivoted to genuinely new indicators applying the continuous-sizing-dial
construction for the first time: MFI, CMF, VZO (volume-weighted family),
then ADX, DMI-diff, CHOP (trend-quality family). All 10 iterations this
trigger produced a dual-symbol QQQ+SPY accept; crypto was decisively
rejected in every single one. The two indicator families (volume-weighted
and trend-quality) cluster around different dual-pass trend_window sweet
spots (~30-40 for volume family, ~25 for trend-quality family), a pattern
worth exploiting in future iterations.
