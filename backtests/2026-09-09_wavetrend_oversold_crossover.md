# WaveTrend Oscillator (LazyBear) Oversold Crossover — Backtest Report

**Date:** 2026-09-09 | **Strategy file:** `strategies/2026-09-09_wavetrend_oversold_crossover.py` | **Outcome: REJECTED**

## Hypothesis
Per pineify.app's WaveTrend Oscillator Pine Script guide (formula) and
Bing's AI-overview aggregation of the indicator's own trading rules
(browser_exec fallback — web_search DuckDuckGo returned "No results found"
for the raw query), WaveTrend normalizes price deviation by its own
volatility. Formula: ap=HLC3, esa=EMA(ap,N), d=EMA(|ap-esa|,N),
ci=(ap-esa)/(0.015*d), WT1=EMA(ci,M), WT2=SMA(WT1,4). Source's explicit
"Golden Cross" rule: long when WT1 crosses above WT2 while below the
oversold zone (~-60), explicitly filtering out neutral-zone crossovers.

Sources: https://pineify.app/pine-script/indicators/wave-trend (formula) ;
Bing AI-overview aggregation (entry/exit rules, 6 sources cited by Bing)

## Grid test (oversold_level=[-50,-60,-70] x avg_len=[14,21], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 72 cells total, 4 passed (pass_fraction 0.056 — among the lowest in this repo's history)
- By asset class: equity 4/36, crypto 0/36 (decisive fail)
- By vol regime: low 1/24, mid 2/24, high 1/24
- Best cell: oversold_level=-70/avg_len=21, SPY high-vol, Sharpe 1.88
- Best avg-across-regime config: QQQ avg_len=14/oversold=-50 avg Sharpe 1.09

## Full-sample direct check (avg_len=14, oversold_level=-50, best grid config)

| Metric | QQQ | SPY |
|---|---|---|
| Trade count | 24 | 21 |
| Full-sample Sharpe | 0.816 **FAIL** | 0.194 **FAIL** (decisive) |
| Max Drawdown | 0.173 (informational) | 0.152 (informational) |

## Verdict
**REJECTED (decisive).** Even the best full-sample grid config's Sharpe
(0.816 QQQ, 0.194 SPY) falls well short of the 1.0 threshold, and SPY's
result is a clear decisive miss rather than a near-miss. The grid's 5.6%
pass fraction is one of the lowest recorded in this repo, reflecting that
requiring both a WT1/WT2 crossover AND the -60-oversold-zone condition
simultaneously is too restrictive to produce a robust signal on daily
equity bars (the indicator's more typical use is intraday/shorter
timeframes per several source pages' "best timeframe" notes, though this
particular source set didn't explicitly caveat timeframe suitability).
Crypto rejected decisively (0/36 grid cells).
