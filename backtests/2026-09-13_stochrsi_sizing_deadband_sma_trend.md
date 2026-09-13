# StochRSI Continuous Sizing + Exposure-Change Deadband on SMA(200) — Backtest Report

**Date:** 2026-09-13 | **KB id:** 2026-09-13-080 | **Outcome:** ACCEPTED (QQQ, all 5 validators, narrow TC margin); SPY rejected (Sharpe + TC fail); crypto decisively rejected

## Hypothesis
StochRSI = 100*(RSI-lowest(RSI,n))/(highest(RSI,n)-lowest(RSI,n)), applying the Stochastic
formula to RSI values, bounded [0,100]. Per wallstreetmojo.com/investopedia.com/sdk-trading.com
(web_search): "far more sensitive than either parent... catching turns earlier but firing many
false signals" — an explicit noise warning. Given this cron trigger's two consecutive findings
that fast-reacting bounded oscillators (CMO, UO) need a deadband to survive transaction costs
(2026-09-13-078, -079), this strategy builds the deadband in from the start rather than testing
a doomed raw version first: exposure = clip(base_exposure + stochrsi_sensitivity*((stochrsi-50)/50),
0, leverage_cap) on SMA(200) trend gate, with exposure held within `deadband` of last update.

## Grid test (Step 6)
`scripts/run_grid_stochrsi_deadband.py`, param_grid: deadband∈{0.10,0.15,0.20},
stochrsi_sensitivity∈{0.4,0.6}, base_exposure∈{0.8,1.0}; symbols equity={QQQ,SPY}
crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3. 2017-01-01 to 2026-09-01.

- total_cells=144, passed=36, **pass_fraction=0.25**
- by_asset_class: equity 36/72; **crypto 0/72 (decisive fail)**
- by_vol_regime: low 24/48, mid 12/48, **high 0/48**
- best_cell: SPY, deadband=0.20, stochrsi_sensitivity=0.4, base_exposure=0.8, low-vol, Sharpe=2.70

## Single-config validation (Step 7) — best config deadband=0.20, stochrsi_sensitivity=0.4, base_exposure=0.8

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>1.0) | **PASS** 1.188 | **FAIL** 0.893 |
| Max Drawdown (<0.25) | PASS 0.181 | PASS 0.160 |
| Transaction cost survival (net Sharpe >0.5 @10bps) | **PASS (narrow)** 0.567 (371 trades) | **FAIL** 0.192 (384 trades) |
| Walk-forward (4-split, ≥0.75 pass) | PASS 1.0 | PASS 0.75 |
| Parameter sensitivity (rel. std <0.5) | PASS 0.030 | PASS 0.019 |

## Decision: ACCEPTED for QQQ (all 5 validators pass, though TC margin is narrow: 0.567 vs 0.5
threshold — StochRSI's documented extra sensitivity vs RSI/CMO/UO shows up as still-elevated
turnover (371 trades) even with a 0.20 deadband, the widest tested this cron trigger). SPY
FAILS both Sharpe and TC decisively — unlike the CMO/UO deadband fixes where SPY was only a
Sharpe near-miss with TC already passing, here StochRSI's extra noise pushes SPY's TC result
into outright failure too. Crypto grid decisively rejected (0/72).

## Note for future iterations
Third data point in the "bounded-oscillator continuous sizing dial" turnover spectrum this
cron trigger: %B/Aroon/Williams %R (smooth enough, no deadband needed) < CMO (needs
deadband=0.10) < StochRSI (needs deadband=0.20, still narrow TC margin on QQQ, fails outright
on SPY) ≈ Ultimate Oscillator (needs deadband=0.20). StochRSI's "most sensitive of the RSI
family" reputation is confirmed empirically — not worth pushing the deadband wider without
also lowering `stochrsi_sensitivity`, which was not swept above 0.6 this iteration.
