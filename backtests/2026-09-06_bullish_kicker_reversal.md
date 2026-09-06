# Bullish Kicker Reversal Strategy — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_bullish_kicker_reversal.py`
**Source:** https://www.quantifiedstrategies.com/bullish-kicker-candlestick-pattern/

## Hypothesis

Bullish Kicker (bearish Day1 candle in a downtrend, Day2 gaps up above
Day1's entire open with minimal lower wick and closes bullish) signals a
forceful overnight sentiment reversal; long entry on Day2 close, stop below
Day2's low, exit on stop or a max_hold_days time-stop.

## Single-config validator results (max_wick_pct=0.15, trend_window=50)

| Symbol | Sharpe | Threshold | Pass | Max DD | Threshold | Pass |
|---|---|---|---|---|---|---|
| QQQ | -0.267 | 1.0 | FAIL | 0.112 | 0.25 | PASS |
| SPY | 0.777 | 1.0 | FAIL | 0.059 | 0.25 | PASS |

Both equity tickers fail Sharpe decisively at this configuration -- QQQ is
outright negative, SPY is a moderate near-miss.

## Grid test summary

`param_grid={"max_wick_pct": [0.10, 0.15, 0.25], "trend_window": [50, 200]}`,
symbols equity=[QQQ, SPY] crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.139 (10/72 cells)**
- by_asset_class: equity 10/36 passed; crypto 0/36 passed (decisive reject for crypto)
- by_vol_regime: low 1/24, mid 2/24, high 7/24 -- most passing cells cluster in the HIGH-vol tercile specifically
- best_cell: max_wick_pct=0.15, trend_window=50, SPY, high-vol, Sharpe 1.53
- worst_cell: same params, QQQ, high-vol, Sharpe -0.87 -- the identical config swings from best to worst cell purely by symbol within the same vol regime, indicating no consistent cross-symbol edge

## Decision: REJECTED

Full-sample Sharpe fails on both QQQ (-0.267, outright negative) and SPY
(0.777, near-miss); grid pass_fraction (13.9%) is elevated relative to some
prior rejected candlestick strategies but the passing cells concentrate
almost entirely in the high-vol tercile and show no consistency across
symbols at the identical parameter combo (SPY 1.53 vs QQQ -0.87 same cell),
indicating the edge is idiosyncratic/regime-specific rather than a genuine
reversal signal. Crypto rejected outright (0/36).

Recorded as a near-miss (elevated grid pass_fraction, high-vol-regime
concentration) worth a future revisit gated explicitly to high-vol regimes
only, but not accepted as a broad-scope strategy as-is.

Walk-forward / transaction-cost / parameter-sensitivity validators skipped
(decisive full-sample Sharpe failure on the primary config already settles
this for the broad-scope hypothesis tested).
