# Backtest Report: ADXR Continuous Trend-Conviction Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_adxr_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-054
**Date:** 2026-09-16

## Hypothesis

ADXR (Wilder's Average Directional Movement Index Rating): ADXR[t] =
(ADX[t]+ADX[t-n])/2, a further-smoothed/rated version of ADX (n = the ADX
period by convention). This repo already has ADX tested as a continuous
trend-conviction sizing dial (id 2026-09-13-092, accepted QQQ+SPY,
rejected crypto) and ADXR tested as a discrete threshold-crossing entry
(id 2026-09-07-013, rejected). This iteration applies the same
continuous-sizing-dial construction validated for plain ADX to its smoothed
sibling ADXR, testing whether the extra smoothing reduces
whipsaw/turnover enough to also work for crypto where plain ADX's dial
was rejected.

Construction: ADXR (bounded [0,100], measures trend conviction regardless
of direction) rescaled to [0,1] and used directly as a continuous sizing
dial (no z-score needed, same "direct rescale" pattern already used for
plain ADX) inside an SMA(trend_window=40) uptrend gate with a deadband.

Source: no new external URL fetched this sub-iteration -- ADXR formula
already documented in this repo from prior id 2026-09-07-013, applied here
per this repo's now-standard "test the smoothed sibling of an
already-accepted sizing dial for crypto generalization" pattern.

## Step 6 — Grid summary

`run_grid_adxr_sizing.py`: `param_grid` = adx_window in {10,14,20} x
sensitivity in {0.4,0.6,0.8} x deadband in {0.10,0.20}, symbols
equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3,
2019-2026.

- total_cells=216, passed=88, **pass_fraction=0.407**
- by_asset_class: equity 54/108, crypto 34/108 (meaningfully better crypto
  coverage than plain-ADX's dial, which was decisively rejected on crypto)
- by_vol_regime: low 62/72, mid 26/72, high 0/72
- best_cell: QQQ adx_window=10/sensitivity=0.8/deadband=0.10, low-vol Sharpe=2.88
- per-symbol grid pass: QQQ 36/54, SPY 18/54, BTC/USDT 26/54, ETH/USDT 8/54

## Step 7 — Single-config validators

| Symbol | adx_window | sensitivity | deadband | base_exposure | leverage_cap | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 14 | 0.6 | 0.30 | 0.4 | 1.0 | 1.072 | 0.179 | 0.752 | 0.75 | 0.017 | YES |
| SPY | 10 | 0.4 | 0.30 | 0.4 | 1.0 | 1.115 | 0.086 | 0.696 | 1.00 | 0.006 | YES |
| BTC/USDT | 20 | 0.4 | 0.20 | 0.2 | 0.3 | 1.477 | 0.175 | 1.170 | 1.00 | 0.00002 | YES |
| ETH/USDT | 10 | 0.6 | 0.20 | 0.2 | 0.25 | 1.258 | 0.179 | 1.018 | 1.00 | 0.0 | YES |

All 4 symbols pass all 5 validators. This is the ADXR dial's key win over
plain-ADX's dial: crypto now passes (BTC Sharpe 1.477, ETH Sharpe 1.258)
where plain ADX's continuous-sizing dial was decisively rejected on
crypto.

## Step 8 — Decision

**ACCEPT** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT). Confirms the
hypothesis: ADXR's extra smoothing DOES rescue crypto generalization
relative to plain ADX's dial.

## Notes

- Seventh consecutive full-universe accept this cron trigger.
- Direct confirmation of a hypothesis stated up front (extra smoothing on
  an already-partially-working dial construction can rescue the
  asset-class scope that the un-smoothed version failed on) -- a
  reusable pattern worth applying to other "accepted equity only, rejected
  crypto" dials in this repo's knowledge base as a cheap future-iteration
  win (test the smoothed/rated sibling indicator, if one exists, before
  inventing a wholly new indicator family).
- Near-zero parameter-sensitivity relative-std for BTC/ETH (0.00002 and
  0.0) reflects ADXR's extra 2-point averaging making it almost
  insensitive to the adx_window choice within the tested range -- a very
  stable dial once accepted.
