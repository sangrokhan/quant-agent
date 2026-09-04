# Backtest Report: RWI Statistical Trend Confirmation (2026-09-04)

**Hypothesis:** Random Walk Index (Michael Poulos) compares actual price
movement to a random-walk null hypothesis: RWI High = (High -
Low[n bars ago]) / (ATR(n)*sqrt(n)), RWI Low = (High[n bars ago] - Low) /
(ATR(n)*sqrt(n)). Per LightningChart's explainer, RWI High > threshold
(1.0) while RWI Low < threshold signals a statistically-significant
uptrend. This strategy: long entry when RWI High crosses above threshold
while RWI Low stays below it; exit when RWI High drops below threshold,
RWI Low overtakes RWI High, or a max_hold_days time-stop. Source:
https://lightningchart.com/blog/trader/random-walk-index/. First Random
Walk Index strategy in this repo -- distinct from VHF/ADX/Choppiness Index
(already tested trend-strength concepts) since RWI compares directly to a
statistical random-walk null hypothesis.

**Strategy file:** `strategies/2026-09-04_rwi_statistical_trend_confirm.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: n[10,14,20], rwi_threshold[1.0,1.2], max_hold_days[15,25];
symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 96, passed_cells: 10, pass_fraction: 0.104
by_asset_class: equity 10/72, crypto 0/24
by_vol_regime: low 10/24, mid 0/24, high 0/24
best_cell: SPY, low-vol, n=20/rwi_threshold=1.2/max_hold_days=15 -> Sharpe 1.925
worst_cell: SPY, mid-vol, n=14/rwi_threshold=1.2/max_hold_days=15 -> Sharpe -0.761
```

## Verdict: **REJECTED**

Grid pass_fraction of 10.4% (10/96) is decisive -- passes are concentrated
exclusively in the low-vol regime (10/24, vs 0/24 mid, 0/24 high) and 0/24
on crypto. No single-config full-sample validator confirmation run given
this decisive grid failure (per RESEARCH_LOOP.md Step 7 guidance). The RWI
crossover + confirmation setup only identifies "genuine" trends in a
narrow low-volatility slice, which is exactly the regime where distinguishing
trend from randomness matters least (calm markets tend to trend gently
regardless of statistical confirmation); it fails to add value in the
higher-vol regimes where the random-walk-vs-trend distinction should
theoretically matter most.
