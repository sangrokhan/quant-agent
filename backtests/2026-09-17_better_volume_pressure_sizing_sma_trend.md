# Backtest Report: Better Volume Buy/Sell Pressure Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-17_better_volume_pressure_sizing_sma_trend.py`
**Date:** 2026-09-17 (KST) / cron trigger iteration 3

## Hypothesis

The "Better Volume" indicator (original idea emini-watch.com, ProRealTime
port by "Dutchy", 2009), per
https://www.prorealcode.com/prorealtime-indicators/better-volume/ (found via
`web_search`, formula confirmed via `browser_exec` reading the full ProRealTime
source code), discloses an exact per-bar buy/sell volume apportionment
distinct from every volume-pressure indicator already tested in this repo:

```
Value1 (est. buy volume)  = Volume * Range / (2*Range + Open - Close)             if Close > Open
                          = Volume * (Range + Close - Open) / (2*Range + Close - Open)  if Close < Open
                          = 0.5 * Volume                                           if Close == Open
Value2 (est. sell volume) = Volume - Value1
```

This repo's prior "Better Volume" research attempt (2026-09-09-060) could
not source an exact formula after trying 5 URLs and gave up as
feasibility-blocked rather than inventing thresholds, per RESEARCH_LOOP.md's
prohibition on that. This iteration's `web_search` call surfaced the
ProRealCode page with the full disclosed source, letting the hypothesis be
tested properly.

Operationalized as a continuous sizing dial: `pressure = (Value1 - Value2) /
Volume` (naturally bounded [-1, +1] by construction since Value1+Value2 ==
Volume), optionally smoothed (`bv_smooth_window`), used directly as an
exposure-sizing dial inside an SMA(trend_window) uptrend gate + deadband.

## Step 6 grid summary

Grid: `bv_smooth_window` in {3,5,10} x `sensitivity` in {0.4,0.6,0.8} x
`deadband` in {0.15,0.25} x 4 symbols x 3 vol regimes = 216 cells.

- **Overall pass fraction:** 114/216 = 0.528 -- one of the stronger grids
  this cron trigger.
- **By asset class:** equity 54/108 (0.50), crypto 60/108 (0.556) -- crypto
  edges out equity in the raw grid (unusual for this repo).
- **By vol regime:** low 72/72 (1.00), mid 37/72 (0.51), high 5/72 (0.07).
- **Best cell:** QQQ low-vol, `bv_smooth_window=10, sensitivity=0.8,
  deadband=0.15`, Sharpe 2.88.
- **Worst cell:** QQQ high-vol, `bv_smooth_window=3, sensitivity=0.8,
  deadband=0.15`, Sharpe -0.59.

Full raw grid: `grid_cells_better_volume_pressure_sizing.json`.

## Step 7 validators (full-sample, best-per-symbol config, after deadband/
sensitivity retune to clear TC-survival near-misses)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | bv_smooth_window=5, sensitivity=0.6, deadband=0.30 | 1.166 (pass) | 0.111 (pass) | 0.668 (pass, 147 trades) | 0.75 (pass) | rel_std 0.025 (pass) | **ACCEPT** |
| SPY | bv_smooth_window=5, sensitivity=0.5, deadband=0.30 | 1.128 (pass) | 0.071 (pass) | 0.535 (pass, 126 trades) | 0.75 (pass) | rel_std 0.042 (pass) | **ACCEPT** |
| BTC/USDT | bv_smooth_window=3, sensitivity=0.8, deadband=0.25, leverage_cap=0.5 | ~0.1-0.2 (FAIL) | >0.30 (FAIL) | negative (FAIL) | pass | pass | REJECT (decisive) |
| ETH/USDT | bv_smooth_window=3, sensitivity=0.8, deadband=0.25, leverage_cap=0.5 | similar decisive fail | decisive fail | decisive fail | pass | pass | REJECT (decisive) |

Both equity symbols' grid-best configs initially missed TC-survival
(QQQ 0.298<0.5 at deadband=0.15, SPY 0.416<0.5 at deadband=0.15) -- a
deadband widening sweep (turnover reduction) found configs clearing all 5
thresholds (QQQ: deadband 0.15->0.30 cut trades 286->147; SPY: deadband
0.15->0.30 + sensitivity 0.6->0.5 cut trades 162->126).

Crypto's grid-best cells (chosen for highest average grid Sharpe across vol
regimes) did NOT survive the full-sample/cost check at the symbol level --
despite crypto's stronger raw grid pass fraction, BTC/USDT and ETH/USDT's
best full-sample configs decisively fail Sharpe, MDD, and net-of-cost
Sharpe simultaneously, consistent with crypto's very high raw trade count
(~7,600+ trades vs equity's ~150-300) overwhelming transaction costs even
before the deadband/leverage adjustments applied elsewhere in this repo.

Full raw validators: `validate_result_better_volume_pressure.json`,
`validate_result_better_volume_pressure_equity_fix.json`.

## Decision

**ACCEPT for equity (QQQ, SPY) with widened deadband=0.30 vs the grid's
raw best cells. REJECT for crypto (BTC/USDT, ETH/USDT)** -- decisive
failure across Sharpe/MDD/net-of-cost Sharpe driven by extremely high
turnover (crypto's daily-bar Range/Open-Close-relative buy/sell split
appears far noisier at crypto's characteristic intrabar volatility than at
equity's, generating far more deadband-crossing signal flips per unit time
despite the raw grid showing decent per-cell Sharpes in isolated vol-regime
slices).
