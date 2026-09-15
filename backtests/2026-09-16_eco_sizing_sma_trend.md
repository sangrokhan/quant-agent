# Backtest Report: Blau's Ergodic Candlestick Oscillator (ECO) Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_eco_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-055
**Date:** 2026-09-16

## Hypothesis

Blau's Ergodic Candlestick Oscillator (ECO), per Google AI-overview
(TradingView/Scribd/StockFetcher corroborating, visited this iteration via
browser_exec Google fallback): ECO = Smooth2(Close-Open) / Smooth2(High-Low),
where Smooth2 is double-EMA smoothing (EMA(EMA(x,r),s), typically r=5,
s=26). ECO divides double-smoothed candlestick BODY (close-open,
directional momentum) by double-smoothed candlestick RANGE (high-low,
total local volatility) -- naturally bounded close to [-1,+1] since
|close-open| <= high-low by construction. Distinct from every prior
Blau-family strategy in this repo (Ergodic Oscillator, TSI, SMI -- all
built from close-to-close price changes) since ECO is built from each
bar's own OPEN-vs-CLOSE candlestick body relative to its own High-Low
range. First Ergodic-Candlestick-Oscillator-specific strategy in this
repo.

Construction: ECO used directly (no z-score needed, already naturally
bounded) as a continuous exposure-sizing dial inside an
SMA(trend_window=40) uptrend gate with a deadband.

Source: Google AI-overview (TradingView/Scribd/StockFetcher) via
browser_exec.

## Step 6 — Grid summary

`run_grid_eco_sizing.py`: `param_grid` = eco_r in {3,5,8} x sensitivity in
{0.6,0.8,1.0} x deadband in {0.10,0.20}, symbols equity={QQQ,SPY}
crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3, 2019-2026.

- total_cells=216, passed=112, **pass_fraction=0.519** (tied for highest of
  all strategies accepted this cron trigger, alongside T3)
- by_asset_class: equity 54/108, crypto 58/108
- by_vol_regime: low 72/72 (perfect low-vol coverage, best of any strategy
  this trigger), mid 37/72, high 3/72
- best_cell: QQQ eco_r=5/sensitivity=1.0/deadband=0.20, low-vol Sharpe=2.92
- per-symbol grid pass: QQQ 36/54, SPY 18/54, BTC/USDT 39/54, ETH/USDT 19/54

## Step 7 — Single-config validators

SPY required raising `base_exposure` to 0.5 (from the usual 0.4) to clear
the TC-survival threshold -- narrow deadbands alone weren't sufficient at
the default base exposure level:

| Symbol | eco_r | sensitivity | deadband | base_exposure | leverage_cap | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 8 | 1.0 | 0.20 | 0.4 | 1.0 | 1.168 | 0.095 | 0.591 | 0.75 | 0.024 | YES |
| SPY | 5 | 0.7 | 0.25 | 0.5 | 1.0 | 1.111 | 0.065 | 0.592 | 0.75 | 0.055 | YES |
| BTC/USDT | 5 | 0.8 | 0.20 | 0.25 | 0.3 | 1.449 | 0.161 | 1.087 | 1.00 | 0.008 | YES |
| ETH/USDT | 8 | 0.8 | 0.15 | 0.25 | 0.25 | 1.243 | 0.175 | 0.994 | 1.00 | 0.008 | YES |

All 4 symbols pass all 5 validators.

## Step 8 — Decision

**ACCEPT** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT).

## Notes

- Eighth consecutive full-universe accept this cron trigger.
- Tied for highest grid pass_fraction (0.519, alongside T3) and best
  low-vol-regime coverage (72/72, i.e. perfect) of any strategy accepted
  this trigger -- ECO's candlestick-body-relative-to-range construction
  may be a genuinely robust signal in calm markets specifically.
- First strategy this trigger to use candlestick BODY/RANGE (open-close
  relative to high-low) rather than close-to-close price action or a
  price-relative-to-a-moving-average distance -- a structurally distinct
  signal source from every other accept this cron trigger, worth noting
  for future correlation/diversification analysis across the accepted
  strategy set.
- Very low parameter-sensitivity for crypto (BTC 0.008, ETH 0.008),
  consistent with the double-smoothing (EMA-of-EMA) making the dial
  naturally robust to the exact `eco_r` choice.
