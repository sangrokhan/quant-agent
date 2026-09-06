# Bullish Harami Reversal Strategy — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_bullish_harami_reversal.py`
**Sources:** https://www.tradingview.com/scripts/hammer/ (Harami sizing rule,
already used for Hammer/Piercing Line strategies), Dukascopy Harami guide
and LiteFinance Harami guide (surfaced via Google SERP fallback after
web_search failure).

## Hypothesis

Bullish Harami (large bearish Day1 candle in a confirmed downtrend, followed
by a smaller bullish Day2 candle whose body is fully contained inside Day1's
body, Day2 body <= 60% of Day1 body) signals a reversal; long entry on Day2
close, stop below Day1's low, or a max_hold_days time-stop.

## Single-config validator results (harami_body_ratio=0.6, trend_window=50, max_hold_days=15)

| Symbol | Sharpe | Threshold | Pass | Max DD | Threshold | Pass |
|---|---|---|---|---|---|---|
| QQQ | 0.333 | 1.0 | FAIL | 0.083 | 0.25 | PASS |
| SPY | 0.651 | 1.0 | FAIL | 0.089 | 0.25 | PASS |

Decisive Sharpe failure on both equity tickers at the default parameterization
(pattern signal is real -- low drawdown, moderate trade count ~140-160 -- but
risk-adjusted return doesn't clear the 1.0 Sharpe bar).

## Grid test summary

`param_grid={"harami_body_ratio": [0.5, 0.6, 0.75], "trend_window": [50, 200]}`,
symbols equity=[QQQ, SPY] crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.042 (3/72 cells)**
- by_asset_class: equity 3/36 passed; crypto 0/36 passed (decisive reject for crypto)
- by_vol_regime: low 0/24, mid 2/24, high 1/24
- best_cell: harami_body_ratio=0.75, trend_window=50, QQQ, mid-vol, Sharpe 1.33
- worst_cell: harami_body_ratio=0.5, trend_window=50, QQQ, low-vol, Sharpe -1.00

Only a looser body-ratio (0.75, i.e. less-strict Harami definition, closer
to any-smaller-body-inside-larger-body) passes, and only in isolated
vol-regime slices -- not a robust broad-scope edge.

## Decision: REJECTED

Full-sample Sharpe fails decisively on both QQQ (0.333) and SPY (0.651) at
the source-recommended default (0.6 body ratio); grid pass_fraction (4.2%)
confirms this isn't a parameterization artifact. Crypto rejected outright
(0/36). Max drawdown passes comfortably in all cases -- this is a low-risk
but insufficiently profitable signal, not a risk-management failure.

Walk-forward / transaction-cost / parameter-sensitivity validators skipped
(suggested_workload=max, but decisive full-sample + grid failure already
settles this).
