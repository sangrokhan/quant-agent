# Backtest Report: T3 (Tillson) Distance Continuous Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_t3_dist_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-051
**Date:** 2026-09-16

## Hypothesis

Tillson's T3 moving average (TradingPedia/HaasOnline; already documented in
this repo from prior ids 2026-09-04-131/2026-09-05-090/2026-09-06-108 --
full e1..e6/c1..c4 coefficient derivation confirmed via a fresh Google
query this iteration since prior entries didn't record it):
e1=EMA(close,period), e2..e6 cascaded EMAs of the prior stage; with volume
factor b (default 0.7): c1=-b^3, c2=3b^2+3b^3, c3=-6b^2-3b-3b^3,
c4=1+3b+b^3+3b^2; T3 = c1*e6 + c2*e5 + c3*e4 + c4*e3. This repo has 3 prior
T3/Coral entries, all using T3 as a DISCRETE trigger (slope-flip near-miss,
price-crosses-T3 accepted-SPY-only, dual-T3-crossover rejected) -- none as
a continuous sizing dial. This iteration reinterprets T3 per this repo's
established distance-from-MA continuous-sizing-dial pattern (cf. PMO, RVI,
DPO), testing whether T3's smoothness (near-zero lag) makes a
close-minus-T3 distance dial less noisy than the discrete crossovers
already tried.

Construction: percent-distance of close from its own T3(t3_window, b=0.7),
rolling z-scored and tanh-squashed, used as a continuous exposure-sizing
dial inside an SMA(trend_window=40) uptrend gate with a deadband.

Source: Google AI-overview (TradingPedia/HaasOnline) via browser_exec.

## Step 6 — Grid summary

`run_grid_t3_dist_sizing.py`: `param_grid` = t3_window in {5,10,15} x
sensitivity in {0.4,0.6,0.8} x deadband in {0.10,0.20}, symbols
equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3,
2019-2026.

- total_cells=216, passed=112, **pass_fraction=0.519** (highest of the four
  strategies accepted this cron trigger)
- by_asset_class: equity 54/108, crypto 58/108
- by_vol_regime: low 68/72, mid 29/72, high 15/72 (first strategy this
  trigger to pass ANY high-vol-regime cells, 15/72)
- best_cell: QQQ t3_window=15/sensitivity=0.4/deadband=0.20, low-vol Sharpe=2.86
- per-symbol grid pass: QQQ 29/54, SPY 25/54, BTC/USDT 44/54, ETH/USDT 14/54

## Step 7 — Single-config validators

| Symbol | t3_window | sensitivity | deadband | base_exposure | leverage_cap | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 15 | 0.4 | 0.30 | 0.4 | 1.0 | 1.435 | 0.085 | 0.922 | 1.00 | 0.174 | YES |
| SPY | 10 | 0.4 | 0.30 | 0.4 | 1.0 | 1.326 | 0.070 | 0.648 | 1.00 | 0.106 | YES |
| BTC/USDT | 5 | 0.6 | 0.20 | 0.25 | 0.3 | 1.398 | 0.143 | 0.571 | 1.00 | 0.055 | YES |
| ETH/USDT | 15 | 0.5 | 0.20 | 0.20 | 0.3 | 1.279 | 0.163 | 1.047 | 1.00 | 0.095 | YES |

All 4 symbols pass all 5 validators.

## Step 8 — Decision

**ACCEPT** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT).

## Notes

- Fourth consecutive full-universe accept this cron trigger (after Elder
  AutoEnvelope 2026-09-16-048, Acceleration Bands 2026-09-16-049, FCO
  2026-09-16-050).
- BTC's TC-survival margin is thin (net Sharpe 0.571, threshold 0.5,
  turnover 364 trades at t3_window=5) -- BTC prefers a shorter T3 window
  than ETH (5 vs 15), unusual since BTC and ETH configs are normally
  similar in this repo; flagged for future revisit if a longer BTC window
  is tried.
- Highest grid pass_fraction (0.519) and first strategy this cron trigger
  to clear any high-vol-regime cells (15/72) -- T3's low-lag smoothing may
  genuinely generalize better across volatility regimes than the z-scored
  raw-indicator dials used in the prior three accepts.
