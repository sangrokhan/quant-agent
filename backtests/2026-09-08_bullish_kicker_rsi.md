# Bullish Kicker (RSI-Confluence) — Backtest Report

**Date:** 2026-09-08 | **Strategy file:** `strategies/2026-09-08_bullish_kicker_rsi.py` | **Outcome: REJECTED**

## Hypothesis
Per wrtrading.com's Bullish Kicker construction rules (browser_exec
fallback — web_search DuckDuckGo returned "No results found") and Bing's
AI-overview aggregation of trading rules, the Bullish Kicker is a 2-candle
reversal: bearish candle1 closing near its low, followed by candle2 that
gaps up (opens at/above candle1's open, no body overlap with candle1's
close) and is itself bullish. Distinct from plain Bullish Engulfing
(tested multiple times, e.g. 2026-09-04-102/2026-09-08-024/2026-09-09-034)
via the explicit gap/no-overlap requirement. Source's own recommendation:
RSI<30-and-turning-up confluence filter; stop-loss below candle1's low.

Sources: https://wrtrading.com/candlestick-pattern/bullish-kicker ;
Bing AI-overview (2 aggregated sources) for entry/exit/RSI-confluence rules

## Grid test (near_low_pct=[0.3,0.5] x rsi_oversold=[30,40], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 48 cells total, 3 passed (pass_fraction 0.0625 — one of the lowest in
  this repo's history)
- By asset class: equity 3/24, crypto 0/24 (decisive fail)
- By vol regime: low 1/16, mid 2/16, high 0/16
- Best cell: near_low_pct=0.5/rsi_oversold=40, SPY low-vol, Sharpe 1.40

## Full-sample direct check (near_low_pct=0.5, rsi_oversold=40, the loosest/best-performing grid config)

| Metric | QQQ | SPY |
|---|---|---|
| Trade count | 19 | 12 |
| Full-sample Sharpe | 0.295 **FAIL** | -0.176 **FAIL** (negative) |

## Verdict
**REJECTED (decisive, feasibility + performance).** Even at the loosest
tested parameter combination (near_low_pct=0.5, i.e. relaxing candle1's
"closes near its low" requirement to the bottom half of its range, and
rsi_oversold=40 rather than the source's stricter 30), the pattern
generates only 12-19 trades full-sample and produces a negative-to-weak
Sharpe on both equity tickers. The grid's 6.25% pass fraction is among the
lowest recorded in this repo, indicating the pattern's strict
gap/no-overlap construction combined with the RSI confluence filter is too
rare and/or non-predictive to form a viable strategy on QQQ/SPY over
2019-2026. Crypto rejected decisively (0/24 grid cells). Full validator
suite (walk-forward, TC-survival, param-sensitivity) skipped since the
full-sample Sharpe already fails decisively on both symbols at the best
grid config.
