# CFTC COT WTI Crude Oil Commercial-Hedger Extreme-Follow — Backtest Report

**Hypothesis:** WTI crude oil (USO) commercial hedger net position
(comm_long - comm_short) percentile-ranking in the top decile of its
trailing distribution (commercials near-least-short, "smart money" less
worried about downside) is a bullish follow signal. Third COT strategy
this cron trigger, third distinct market/category (Bitcoin leveraged-money
extreme fade -037 rejected, Gold non-commercial trend-confirm -038
accepted, this one: WTI commercial-hedger extreme-follow).

**Sources:**
- https://www.google.com/search?q=crude+oil+COT+commercial+hedgers+net+position+extreme+contrarian+trading+signal+rule (browser_exec Google SERP; TradeAlgo/cotinsight.com/TradingView)
- https://publicreporting.cftc.gov/resource/jun7-fc8e.json (CFTC Legacy COT API, `WTI FINANCIAL CRUDE OIL - NEW YORK MERCANTILE EXCHANGE` market, 391 weekly rows 2019-03 to present)

**Data:** USO/XLE daily OHLCV via `load_equity`; BTC/ETH via `load_crypto` (robustness-check-only).

## Grid test

`param_grid = {lookback_weeks: [52,104,156], high_pct: [0.80,0.85,0.90]}`,
`symbols = {equity: [USO,XLE], crypto: [BTC/USDT,ETH/USDT]}`.

- total_cells: 108, passed_cells: 9, **pass_fraction: 0.083**
- by_asset_class: **equity 0/54 passed** (the intended asset class — decisive fail), crypto 9/54 passed (spurious — WTI COT signal has no economic link to crypto price action, applied only as an out-of-sample check)
- by_vol_regime: low 5/36, mid 4/36, high 0/36
- best_cell: lookback_weeks=156, high_pct=0.80, ETH/USDT, low-vol, Sharpe 1.90 (crypto, not meaningful)
- worst_cell: lookback_weeks=52, high_pct=0.85, USO, high-vol, Sharpe -1.59

## Primary-config validation (USO, lookback_weeks=104, high_pct=0.90 — grid's best equity attempt)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full period) | -0.781 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.710 | ≤ 0.35 | **FAIL** |

Decisive fail on both — no further validators run per Step 7 (skip subset
guidance when primary metrics already decisively fail).

## Decision: REJECTED

The intended asset class (WTI crude oil / USO) fails completely (0/54
grid cells, negative full-period Sharpe, 71% max drawdown on the best
attempted config). The only "passing" cells were in crypto — an
out-of-sample robustness-check leg with no economic connection to WTI COT
data, so those passes are noise/overfitting artifacts, not evidence of a
real edge. Strategy file and this report kept as a record of a rejected
attempt.
