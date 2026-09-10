# DSS (Double Smoothed Stochastic, William Blau) Oversold Turn-Up

**Date:** 2026-09-10
**Strategy file:** `strategies/2026-09-10_dss_blau_oversold_turnup.py`
**Knowledge base id:** 2026-09-10-081

## Hypothesis

Per Wealth-Lab's DSS wiki page (visited this iteration,
http://www2.wealth-lab.com/WL5Wiki/DSS.ashx): the Double Smoothed
Stochastic (William Blau) applies two chained EMA smoothings to the raw
Stochastic numerator/denominator BEFORE computing the ratio (a
structurally different smoothing order than %D, which smooths the ratio
AFTER). The source's own worked strategy example: "Buy when DSS turns up
from an oversold level" (their example threshold: 24), "Sell when DSS
turns down" (symmetric). First DSS/Blau strategy in this repo.

## Grid test summary (Step 6)

Equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT) x
`oversold_threshold in [20,24,30]` x `max_hold_days in [15,25]` x
vol_regime_splits=3 = 72 cells.

- total_cells: 72, passed_cells: 6, **pass_fraction: 0.083 (weak)**
- by_asset_class: equity 6/36, **crypto 0/36 (decisive reject)**
- by_vol_regime: low 0/24, mid 4/24, high 2/24 -- unusually
  mid/high-vol-concentrated (opposite of most strategies in this repo)
- best_cell: `oversold_threshold=30, max_hold_days=25`, QQQ, mid-vol,
  Sharpe 2.12

## Full-sample validators on best config (`oversold_threshold=30, max_hold_days=25`)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.007 (pass, marginal) | 0.431 (FAIL) | >= 1.0 |
| Max drawdown | **0.296 (FAIL)** | 0.192 (pass) | <= 0.25 |
| TC survival (10bps/trade) | 0.959 (pass) | 0.383 (FAIL) | >= 0.5 |
| Walk-forward (4 manual date-slices) | 0.75 (pass, 3/4) | 0.5 (FAIL, 2/4) | >= 0.75 |
| Parameter sensitivity (6-cell grid) | rel_std 0.190 (pass) | rel_std 0.266 (pass) | <= 0.5 |

## Decision: REJECT

QQQ marginally clears Sharpe (1.007) but fails max drawdown decisively
(29.6% vs 25% cap) -- an oversold-bounce mean-reversion entry with no
trend/regime filter is vulnerable to catching falling knives during real
drawdowns (2022, 2020 COVID), consistent with the low-vol-regime being the
*worst*-performing slice (0/24) rather than the best, an inversion of
this repo's usual pattern. SPY fails Sharpe, TC-survival, and
walk-forward outright. Crypto rejected decisively (0/36). Overall
low grid pass_fraction (0.083) confirms this is not a robust edge.
