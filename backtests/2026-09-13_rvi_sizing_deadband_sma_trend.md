# RVI Continuous Sizing + Exposure-Change Deadband on SMA(200) Trend Gate — Backtest Report

**Date:** 2026-09-13 | **KB id:** 2026-09-13-081 | **Outcome:** ACCEPTED (QQQ, all 5 validators); SPY near-miss (Sharpe 0.729<1.0); crypto decisively rejected

## Hypothesis
Relative Vigor Index (John Ellis) = triangle-weighted 4-period average of (Close-Open)/(High-Low),
bounded ~[-1,1], per bybit.com/tradingsim.com/steema.com/investopedia.com (browser_exec SERP —
web_search DDGS backend returned "no results found" for this exact query, google.com fallback
used per protocol). Repo has 8 prior RVI entries, all binary signal-line-crossover triggers.
Reuses "bounded oscillator as continuous sizing dial + exposure-change deadband" pattern
validated 3x already this cron trigger (CMO-078, UO-079, StochRSI-080): exposure =
clip(base_exposure + rvi_sensitivity*rvi, 0, leverage_cap) on SMA(200) trend gate, held within
`deadband`. RVI is structurally distinct from every prior sizing dial this trigger — measures
intraday close-vs-open conviction relative to daily range (candle-body-based).

## Grid test (Step 6)
`scripts/run_grid_rvi_deadband.py`, param_grid: deadband∈{0.05,0.10,0.15}, rvi_sensitivity∈{0.4,0.6,0.8},
rvi_window∈{10,20}; symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3.
2017-01-01 to 2026-09-01.

- total_cells=216, passed=54, **pass_fraction=0.25**
- by_asset_class: equity 54/108; **crypto 0/108 (decisive fail)**
- by_vol_regime: low 36/72, mid 18/72, **high 0/72**
- best_cell: QQQ, deadband=0.15, rvi_sensitivity=0.4, rvi_window=10, low-vol, Sharpe=2.55

## Single-config validation (Step 7) — best config deadband=0.15, rvi_sensitivity=0.4, rvi_window=10

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>1.0) | **PASS** 1.119 | **FAIL (near-miss)** 0.729 |
| Max Drawdown (<0.25) | PASS 0.181 | PASS 0.172 |
| Transaction cost survival (net Sharpe >0.5 @10bps) | **PASS** 1.024 (79 trades) | **PASS** 0.545 (111 trades) |
| Walk-forward (4-split, ≥0.75 pass) | PASS 1.0 | PASS 0.75 |
| Parameter sensitivity (rel. std <0.5) | PASS 0.017 | PASS 0.030 |

## Decision: ACCEPTED for QQQ (all 5 validators pass, healthy TC margin, only 79 trades over the
sample — RVI's candle-body construction with a rolling-mean smoother turns out to be one of the
LOWER-turnover oscillators tried this trigger, comparable to %B/Aroon/Williams %R rather than
CMO/UO/StochRSI). SPY near-miss (Sharpe fail only, same recurring pattern as every other
accepted sizing overlay this cron trigger). Crypto decisively rejected (0/108).

## Note for future iterations
This is the 6th accepted sizing-overlay variant this cron trigger sharing the identical scope
(QQQ full accept, SPY Sharpe-only near-miss, crypto decisive reject). The pattern is now firmly
established: this repo's SMA(200)-gated continuous-sizing family works robustly for QQQ but not
SPY or crypto, regardless of which bounded oscillator drives the sizing. Future iterations
should consider testing WHY SPY specifically fails (e.g. SPY's lower volatility/beta means the
same base_exposure/sensitivity calibration under-delivers relative to QQQ) rather than
continuing to cycle through oscillator families with the same trend-gate/sizing-dial skeleton.
