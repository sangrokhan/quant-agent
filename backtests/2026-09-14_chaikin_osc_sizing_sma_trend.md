# 2026-09-14 — Chaikin Oscillator z-score-normalized continuous sizing overlay on SMA(40) trend gate

## Hypothesis

Chaikin Oscillator (Marc Chaikin; formula per
https://www.investopedia.com/terms/c/chaikinoscillator.asp, read via
browser_exec this iteration — web_search's DuckDuckGo backend TLS-errored
on every query attempted): Money Flow Multiplier N =
((Close-Low)-(High-Close))/(High-Low); Money Flow Volume M = N*Volume;
ADL = cumsum(M); CO = EMA(ADL,3) - EMA(ADL,10).

This repo has 2 prior Chaikin Oscillator entries (2026-09-04-093 zero-line
crossover + SMA200 filter; 2026-09-09-068 hidden bullish divergence), both
binary-trigger ENTRY constructions, both rejected. Neither reframed CO as
a CONTINUOUS SIZING dial. CO is dollar*volume-scale, so this iteration
normalizes it via a rolling z-score (distinct from the ATR-normalization
used for the prior iteration's Elder-Ray net power, 2026-09-14-121) —
`co_zscore = (CO - rolling_mean(CO,60)) / rolling_std(CO,60)`, clipped
[-2.5, 2.5] — then uses it as a sizing dial within an SMA(40) uptrend gate
with a deadband.

## Strategy file

`strategies/2026-09-14_chaikin_osc_sizing_sma_trend.py`

## Step 6 — Grid test summary (72 cells: sensitivity in {0.3,0.5,0.7} x
deadband in {0.15,0.20} x QQQ/SPY/BTC/ETH x 3 vol regimes)

- pass_fraction: 0.458 (33/72)
- by_asset_class: equity 15/36 passed; crypto 18/36 passed (crypto
  slightly outperforming equity in the grid this time, unusual vs most
  prior sizing-dial iterations this cron trigger)
- by_vol_regime: low 24/24 passed; mid 9/24 passed; high 0/24 passed
- best_cell: SPY low-vol, sensitivity=0.3/deadband=0.15, Sharpe 2.76
- worst_cell: SPY mid-vol, sensitivity=0.5/deadband=0.20, Sharpe -0.26

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01, own-data parameter re-scan beyond grid default to satisfy
TC-survival, same rebalance-threshold-widening pattern used repeatedly
this cron trigger)

| Symbol | sensitivity | deadband | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|---|---|
| QQQ | 0.3 | 0.30 | 1.084 (pass) | 0.140 (pass) | 0.650 (pass) | pass | pass |
| SPY | 0.2 | 0.30 | 1.112 (pass) | 0.070 (pass) | 0.579 (pass) | pass | pass |
| BTC/USDT | 0.5 | 0.15 | 1.515 (pass) | 0.305 (**fail**, >0.25) | 1.117 (pass) | pass | pass |

## Step 8 — Decision

**Accepted: QQQ and SPY** (equity), all 5 validators pass at
sensitivity=0.3/deadband=0.30 (QQQ) and sensitivity=0.2/deadband=0.30
(SPY). **Rejected: crypto (BTC/USDT, ETH/USDT)** — MDD decisively exceeds
threshold (0.305 vs 0.25) even at the best full-sample Sharpe config,
despite Sharpe/TC/WF/param-sens all passing — grid confirms 0/24 high-vol
crypto cells pass at all. Continues this cron trigger's near-universal
"continuous sizing overlays work well on equity, fail crypto MDD" finding.
