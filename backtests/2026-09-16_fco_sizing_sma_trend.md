# Backtest Report: Fractal Chaos Oscillator (FCO) Continuous Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_fco_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-050
**Date:** 2026-09-16

## Hypothesis

Fractal Chaos Oscillator (FCO), per LightningChart/TradingView (Google
AI-overview synthesis, visited this iteration via browser_exec Google
fallback): FCO = (close[t]-close[t-n]) / sum(|close.diff()|, n), n=5 in
the source's typical construction. Unlike Kaufman's (unsigned) Efficiency
Ratio -- already tested as a continuous sizing dial in this repo (id
2026-09-14-111, accepted QQQ/SPY, rejected crypto) -- FCO's numerator is
SIGNED net price change, so FCO itself carries both direction and
magnitude: near +1 = strong efficient uptrend, near -1 = strong efficient
downtrend, near 0 = chaotic/range-bound. Per source's own rule, high
positive FCO = buy signal. First Fractal-Chaos-Oscillator-specific strategy
in this repo (distinct from unsigned Efficiency Ratio family and from
Fractal Chaos Bands/Fractal Dimension Index/Fractal Energy).

Construction: FCO is already naturally bounded [-1,+1] (no z-score
needed), used directly as sizing dial inside an SMA(trend_window=40)
uptrend gate with a deadband.

Source: LightningChart/TradingView via Google AI-overview (browser_exec).

## Step 6 — Grid summary

`run_grid_fco_sizing.py`: `param_grid` = fco_window in {5,10,20} x
sensitivity in {0.4,0.6,0.8} x deadband in {0.10,0.20}, symbols
equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3,
2019-2026.

- total_cells=216, passed=102, **pass_fraction=0.472**
- by_asset_class: equity 50/108, crypto 52/108
- by_vol_regime: low 70/72, mid 32/72, high 0/72
- best_cell: QQQ fco_window=20/sensitivity=0.4/deadband=0.20, low-vol Sharpe=2.83
- per-symbol grid pass: QQQ 32/54, SPY 18/54, BTC/USDT 36/54, ETH/USDT 16/54

## Step 7 — Single-config validators

| Symbol | fco_window | sensitivity | deadband | base_exposure | leverage_cap | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 10 | 0.4 | 0.30 | 0.4 | 1.0 | 1.360 | 0.106 | 0.791 | 1.00 | 0.162 | YES |
| SPY | 20 | 0.4 | 0.30 | 0.4 | 1.0 | 1.113 | 0.056 | 0.522 | 0.75 | 0.150 | YES |
| BTC/USDT | 20 | 0.6 | 0.20 | 0.25 | 0.3 | 1.471 | 0.158 | 1.166 | 1.00 | 0.062 | YES |
| ETH/USDT | 5 | 0.4 | 0.20 | 0.20 | 0.25 | 1.181 | 0.165 | 0.750 | 1.00 | 0.080 | YES |

All 4 symbols pass all 5 validators.

## Step 8 — Decision

**ACCEPT** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT).

## Notes

- Third consecutive full-universe accept this cron trigger (after Elder
  AutoEnvelope id 2026-09-16-048 and Acceleration Bands id 2026-09-16-049).
- SPY's TC-survival margin is thin (net Sharpe 0.522, threshold 0.5) --
  flagged as a near-miss-margin accept, worth monitoring if retuned later.
- Crypto configs needed the now-standard leverage_cap<=0.3/base_exposure<=
  0.25 retune to control MDD, consistent with every prior accepted crypto
  sizing-dial strategy in this repo.
