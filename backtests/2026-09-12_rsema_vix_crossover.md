# Backtest Report: Vitali Apirine Relative VIX Strength EMA (RSEMA) Crossover

**Strategy file:** `strategies/2026-09-12_rsema_vix_crossover.py`
**Source:** Vitali Apirine, TASC 3/2022. Formula reproduced from
https://financial-hacker.com/the-relative-strength-exponential-moving-average/
(fully disclosed C code).

## Hypothesis

A volatility-adaptive EMA of price, whose smoothing rate speeds up when
VIX shows a strong up-day/down-day EMA asymmetry, tracks price with less
lag through volatility regime shifts than a plain EMA. Long when a
companion EMA(periods) crosses above RSEMA, flat otherwise. The source's
own naive default-parameter SPY backtest was unprofitable (vs
buy-and-hold, large drawdowns) — this repo ran an independent grid search
rather than accepting that single untuned result.

## Full-sample parameter search (equity, periods x {5,10,20}, ema_periods x {5,10,20}, multiplier x {5,10,20})

| Symbol | Best config | Best Sharpe |
|---|---|---|
| QQQ | periods=5, ema_periods=20, multiplier=5 | 0.876 |
| SPY | periods=5, ema_periods=20, multiplier=10 | 0.705 |

Both decisively below the min_sharpe=1.0 threshold across the entire
27-combination grid tried per symbol.

## Grid test summary (periods x {5,10}, multiplier x {5,10}, equity {QQQ,SPY} + crypto {BTC/USDT}, vol_regime_splits=3)

- **Total cells:** 36, **passed:** 8, **pass_fraction: 0.222**
- **By asset class:** equity 8/24 (0.333), crypto 0/12 (0.0)
- **By vol regime:** low 7/12 (0.583), mid 0/12 (0.0), high 1/12 (0.083)
- **Best cell:** QQQ low-vol, periods=5/multiplier=5, Sharpe 1.74
- **Worst cell:** BTC/USDT high-vol, periods=10/multiplier=5, Sharpe 0.06

Confirms the source's own honest negative prior: at no full-sample config
does the strategy clear the Sharpe threshold, and the isolated low-vol
grid cell successes don't survive to the full-sample metric.

## Decision: REJECT (decisive)

Best full-sample Sharpe (0.876 QQQ, 0.705 SPY) is well below the 1.0
threshold across the entire tested parameter grid, consistent with the
source's own reported result. Strategy code and this report kept as a
record of a rejected attempt (independently confirms the source's
skepticism rather than just repeating it).
