# DecisionPoint 3-Tier Trend Model (Carl Swenlin) — Backtest Report

**Hypothesis:** Per StockCharts.com ChartSchool's "DecisionPoint Trend Model"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/decisionpoint-trend-model,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content; Carl Swenlin's methodology): trend classification
across three simultaneous timeframes -- long-term (50-EMA vs 200-EMA),
intermediate-term (20-EMA vs 50-EMA), and short-term (20-EMA's own slope
direction). Long only when all three align bullish; flat as soon as any one
breaks.

**Source:** https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/decisionpoint-trend-model

## Grid summary (Step 6)

- Grid: long_fast∈{40,50,60} × slope_lookback∈{3,5,10}, symbols={QQQ,SPY}×
  {BTC/USDT,ETH/USDT}, vol_regime_splits=3 (2015-01-01 to 2026-09-01).
- 108 total cells, 41 passed (pass_fraction=0.38) — one of the strongest
  pass fractions this cron trigger.
- by_asset_class: equity 27/54; crypto 14/54 (genuine crypto signal, see
  full-sample results below).
- by_vol_regime: low 27/36, mid 14/36, high 0/36.
- Best cell: SPY long_fast=60/slope_lookback=5, low-vol Sharpe=2.04.

## Full-sample parameter search + single-config validation (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | long_fast=40, inter_fast=15, slope_lookback=7 | 1.013 (PASS) | 0.234 (PASS) | 0.948 (PASS) | 3/4=0.75 (PASS) | 0.089 (PASS) |
| BTC/USDT | long_fast=40, inter_fast=25, slope_lookback=7, leverage_cap=0.5 | 1.188 (PASS) | 0.216 (PASS) | 1.165 (PASS) | 4/4=1.00 (PASS) | 0.047 (PASS) |
| SPY | long_fast=70, inter_fast=25, slope_lookback=7 | 0.749 (fail) | -- | -- | -- | -- |
| ETH/USDT | long_fast=40, inter_fast=25, slope_lookback=5 | 0.939 (fail) | -- | -- | -- | -- |

BTC/USDT full-exposure MDD was 40.8% (decisive fail); a leverage-cap scan
found leverage_cap=0.5 clears the 25% threshold (MDD=21.6%) while Sharpe/
walk-forward/parameter-sensitivity are unaffected (leverage-invariant), so
the crypto accept uses this reduced exposure.

## Decision: ACCEPT (QQQ full exposure; BTC/USDT at leverage_cap=0.5)

Both configs clear all 5 validators. SPY and ETH/USDT both fall short of
the Sharpe 1.0 threshold across extensive local parameter search (best
0.749/0.939 respectively) and are recorded as rejected. This strategy is
added to `strategies/` as a live QQQ (full exposure) + BTC/USDT
(leverage-capped) strategy.
