# Ultimate Oscillator Continuous Sizing Overlay on SMA(200) Trend Gate — Backtest Report

**Date:** 2026-09-13 | **KB id:** 2026-09-13-077 | **Outcome:** REJECTED (decisive on equity TC + crypto)

## Hypothesis
Ultimate Oscillator (Larry Williams, 1976): BP/TR weighted average across 7/14/28-period
timeframes, bounded 0-100, centerline 50. Source: chartschool.stockcharts.com (browser_exec;
web_extract failed — DDGS backend is search-only, cannot extract). Repo has 6 prior UO
entries, all binary divergence/threshold(30/70) triggers. This iteration reuses the "bounded
oscillator as continuous sizing dial" pattern (accepted for %B/Aroon/Williams %R this cron
trigger): exposure = clip(base_exposure + uo_sensitivity*((uo-50)/50), 0, leverage_cap) on
SMA(200) trend gate.

## Grid test (Step 6)
`scripts/run_grid_uo_sizing.py`, param_grid: uo_fast∈{7,10}, base_exposure∈{0.6,0.8,1.0},
uo_sensitivity∈{0.4,0.6,0.8}; symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT};
vol_regime_splits=3. 2017-01-01 to 2026-09-01.

- total_cells=216, passed=54, **pass_fraction=0.25**
- by_asset_class: equity 54/108; **crypto 0/108 (decisive fail)**
- by_vol_regime: low 36/72, mid 18/72, **high 0/72**
- best_cell: QQQ, uo_fast=10, base_exposure=0.8, uo_sensitivity=0.4, low-vol, Sharpe=2.46

## Single-config validation (Step 7) — best config uo_fast=10, base_exposure=0.8, uo_sensitivity=0.4

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>1.0) | **PASS** 1.105 | **FAIL** 0.791 |
| Max Drawdown (<0.25) | PASS 0.186 | PASS 0.181 |
| Transaction cost survival (net Sharpe >0.5 @10bps) | **FAIL** -0.124 (1826 trades) | **FAIL** -0.252 (1810 trades) |
| Walk-forward (4-split, ≥0.75 pass) | PASS 1.0 | PASS 0.75 |
| Parameter sensitivity (rel. std <0.5) | PASS 0.028 | PASS 0.021 |

## Decision: REJECTED
Same failure mode as CMO (2026-09-13-076) but far more severe: UO's 3-timeframe blend
(7/14/28-period BP/TR ratios) is even noisier day-to-day than a single-window oscillator,
producing ~1800 rebalances over the sample (vs. 562/525 for CMO, and far fewer for the
accepted %B/Aroon/Williams %R variants) — net Sharpe after 10bps costs goes **negative** on
both QQQ and SPY despite QQQ passing raw Sharpe/MDD/walk-forward/parameter-sensitivity.
Crypto grid decisively rejected (0/108). Confirms the emerging pattern from CMO: bounded
oscillators built from un-smoothed period-sums (CMO, UO) are too noisy for continuous-sizing
use without an added smoothing/deadband step, whereas smoother constructions (%B's std-dev
band, Aroon's extreme-recency count, Williams %R's High/Low range) survive transaction costs.

## Note for future iterations
Do not retry raw CMO/UO/other multi-window-sum oscillators as continuous sizing dials without
first EMA-smoothing the oscillator or adding an exposure-change deadband — turnover is the
binding constraint, not the underlying directional Sharpe.
