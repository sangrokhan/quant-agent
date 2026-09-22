# Ehlers Roofing Filter — Vol-Regime-Gate Rescue — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ehlers_roofing_filter_volgate_rescue.py`
**Status:** REJECTED

## Hypothesis

Rescue sub-iteration for this same cron trigger's own 2026-09-22-056 (plain
Ehlers Roofing Filter Filt/Trigger self-lag crossover). 2026-09-22-056's
grid test found the strategy's edge collapsed completely (0/72 cells
passed) in the high-vol tercile while holding up reasonably in low-vol
(0.625 pass rate) and mid-vol (0.236). This sub-iteration adds an explicit
realized-volatility regime gate (this repo's standard construction: 20d
realized vol <= trailing 252d median) as a REQUIRED entry precondition and
an additional exit trigger, on top of the unchanged Filt/Trigger crossover +
SMA trend-filter base logic.

## Grid test summary (Step 6)

`run_strategy_grid`: `hp_period` in {48,60,72}, `lp_period` in {10,14,18},
`trend_window` in {50,100}; symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT
(crypto); `vol_regime_splits=3`.

- **total_cells:** 216, **passed_cells:** 64, **pass_fraction:** 0.296 (vs 0.287 baseline — marginal improvement)
- **by_asset_class:** equity 27/108 (0.250, down from 0.315), crypto 37/108 (0.343, up from 0.259)
- **by_vol_regime:** low 38/72 (0.528), mid 26/72 (0.361), **high 0/72 (0.000, unchanged)**
- **best_cell:** hp_period=72, lp_period=10, trend_window=100 — ETH/USDT, mid-vol, Sharpe 2.27
- **worst_cell:** hp_period=60, lp_period=18, trend_window=100 — BTC/USDT, high-vol, Sharpe -1.78

The high-vol gate (which flattens the strategy during periods it already
avoided being *newly* entering, but does not prevent an existing position
opened just before a vol spike from being force-exited) did not eliminate
the high-vol-tercile collapse — it remains exactly 0/72. Overall
pass_fraction only marginally improved (0.296 vs 0.287) and shifted the
balance from equity-favoring to crypto-favoring, not a clean fix.

## Single-config validation (Step 7) — best grid config (hp=72, lp=10, trend_window=100)

| Validator | QQQ | SPY | ETH/USDT | BTC/USDT | Threshold |
|---|---|---|---|---|---|
| Sharpe ratio | 0.082 FAIL | 0.302 FAIL | 1.005 PASS | 0.284 FAIL | ≥ 1.0 |
| Max drawdown | 0.099 PASS | 0.103 PASS | 0.347 FAIL | 0.311 FAIL | ≤ 0.25 |
| TC survival | -0.081 FAIL | 0.051 FAIL | 0.960 PASS | 0.225 FAIL | ≥ 0.5 |
| Walk-forward (4-split) | 0.75 PASS | 0.75 PASS | 0.50 FAIL | 0.25 FAIL | ≥ 0.75 |
| Parameter sensitivity | 12.3 FAIL | 0.127 PASS | 0.465 PASS | 0.989 FAIL | ≤ 0.5 |

No symbol clears all 5 validators. QQQ and BTC/USDT fail on 3-4 of 5
validators each; SPY and ETH/USDT each fail 2 of 5 (SPY: Sharpe+TC;
ETH/USDT: MDD+walk-forward).

## Decision

**REJECTED.** The explicit high-vol exclusion gate did not resolve the
underlying issue (high-vol collapse persists at 0/72, and the gate
introduces new instability — QQQ's parameter sensitivity blew up to 12.3
relative std, likely from the added vol-gate creating brittle interaction
effects with the trend filter at certain hp/lp combinations). This
confirms the Ehlers Roofing Filter Filt/Trigger crossover construction
itself (not just the missing vol gate) is not a robust standalone edge in
this repo's validator suite. Not recommended for further rescue attempts
without a fundamentally different confirmation/exit mechanism.
