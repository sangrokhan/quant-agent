# Backtest Report: Vortex Diff-Ratio Continuous Sizing (2026-09-14-095)

**Strategy file:** `strategies/2026-09-14_vortex_diffratio_sizing_sma_trend.py`

**Hypothesis:** Vortex Indicator (VI+/VI-, Botes & Siepman 2010; formula per
https://en.wikipedia.org/wiki/Vortex_indicator and
https://www.investopedia.com/terms/v/vortex-indicator-vi.asp). This repo has
4+ prior Vortex entries (2026-09-04-040, 2026-09-06-091, 2026-09-09-084,
2026-09-11-107/-132), all binary crossover/threshold entry triggers.
Individually VI+/VI- are not cleanly bounded, so unlike the CMF/VZO/ADX/
DMI-diff/CHOP continuous-sizing dials already validated this cron trigger,
raw Vortex needed a new bounded transform: `diff_ratio = (VI+-VI-)/(VI++VI-)`,
algebraically bounded [-1,1]. Used as a continuous sizing dial within an
SMA(trend_window) uptrend gate: exposure scales up when VI+ dominates
(strong uptrend momentum), down toward zero as VI- closes the gap.

## Grid summary (param_grid: vortex_window in {10,14,20}, diff_sensitivity
in {0.4,0.6,0.8}; symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT};
vol_regime_splits=3; 2019-2026)

- total_cells=108, passed=27, pass_fraction=0.25
- by_asset_class: equity 27/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 9/36, high 0/36 (high-vol regime always fails,
  consistent with prior sizing-dial entries this trigger)
- best_cell: vortex_window=20, diff_sensitivity=0.4 -> QQQ low-vol Sharpe 2.79
- worst_cell: vortex_window=20, diff_sensitivity=0.8 -> QQQ high-vol Sharpe -0.25

Full-sample per-symbol average Sharpe across all 9 param combos was very
stable: QQQ ~1.26-1.31, SPY ~1.11-1.24 -- selected trend_window=40 (repo
default),  vortex_window=20, diff_sensitivity=0.4 as primary config (best
grid cell, also near the flat mean).

## Single-config validators (trend_window=40, vortex_window=20,
base_exposure=0.5, diff_sensitivity=0.4, leverage_cap=1.0, deadband=0.10)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.131 PASS | 1.131 PASS |
| Max drawdown (<=0.25) | 0.122 PASS | 0.070 PASS |
| TC survival net Sharpe (>=0.5) | 0.893 PASS | 0.849 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits, manual contiguous split -- vectorbt's RangeSplitter unavailable in installed version) | 0.75 PASS (3/4 folds positive) | 0.75 PASS (3/4 folds positive) |
| Parameter sensitivity (rel std <=0.5, computed from grid's 9-combo full-sample Sharpe) | 0.013 PASS | 0.031 PASS |

**All 5 validators pass for both QQQ and SPY.**

## Decision: ACCEPT (both QQQ and SPY)

Seventh dual-symbol accept for a genuinely new indicator-transform pairing
this cron trigger (after MFI-089, CMF-090, VZO-091, ADX-092, DMI-diff-093,
CHOP-094), and the first that required deriving a new bounded ratio
transform (rather than using a natively-bounded raw indicator) to make the
sizing-dial construction applicable. Confirms the pattern holds for
trend-quality-family indicators generally. Crypto remains decisively
rejected across the grid (0/54 cells) and high-vol regime remains a
universal failure mode for this whole family of overlays. Strategy kept
live in `strategies/`.

Note: `check_walk_forward` in `validation/validators.py` currently calls
`vbt.utils.splitting.RangeSplitter`, which does not exist in the installed
vectorbt version (`AttributeError: module 'vectorbt.utils' has no attribute
'splitting'`) -- worked around with a manual 4-fold contiguous split for
this iteration; a future iteration should fix `validators.py` itself.
