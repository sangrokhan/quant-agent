# Volume-Weighted RSI (VWRSI) Recovery Strategy — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_volume_weighted_rsi_recovery.py`
**Source:** https://www.tradingview.com/script/cM6CWwGG-Volume-Weighted-RSI-wbburgin/ (TradingView open-source "Volume-Weighted RSI [wbburgin]")

## Hypothesis

A volume-weighted RSI variant that scales each bar's classic RSI gain/loss
by `(1 + volume_pct_change^2)` (source's stated "square of the volume
change" construction — distinct from MFI's typical-price*volume dollar-flow
weighting already tested in this repo) will produce cleaner oversold
signals: recoveries on shrinking volume get discounted (exhaustion, not
real capitulation) while recoveries on expanding volume get amplified.
Long entry on VWRSI crossing back above an oversold threshold within an
uptrend (close > SMA(trend_window)); exit on overbought, failed-bounce,
trend break, or time-stop.

## Single-config validator results (oversold_threshold=30, trend_window=100)

| Symbol | Sharpe | Threshold | Pass | Max DD | Threshold | Pass |
|---|---|---|---|---|---|---|
| QQQ | -0.240 | 1.0 | FAIL | 0.130 | 0.25 | PASS |
| SPY | 1.010 | 1.0 | PASS (barely) | 0.042 | 0.25 | PASS |

For SPY (the best config): 63 trades.
- **Transaction cost survival**: net Sharpe after 10bps/trade cost = 0.424, threshold 0.5 — **FAIL**.
- **Parameter sensitivity**: relative std across the 6-cell (oversold_threshold x trend_window) grid = 0.528, threshold 0.5 — **FAIL** (barely).
- Walk-forward validator errored on this vectorbt install (`vectorbt.utils.splitting` attribute missing — a pre-existing environment issue, not specific to this strategy) — skipped, noted here rather than silently omitted.

QQQ decisively fails Sharpe on the same config, so this only barely works on
one of the two primary equity tickers, and even there it fails cost
survival and parameter-sensitivity robustness checks.

## Grid test summary

`param_grid={"oversold_threshold": [25, 30, 35], "trend_window": [100, 200]}`,
symbols equity=[QQQ, SPY] crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.083 (6/72 cells)**
- by_asset_class: equity 6/36 passed; crypto 0/36 passed (decisive reject for crypto)
- by_vol_regime: low 0/24, mid 3/24, high 3/24
- best_cell: oversold_threshold=30, trend_window=100, SPY, high-vol, Sharpe 2.42
- worst_cell: oversold_threshold=25, trend_window=100, QQQ, high-vol, Sharpe -1.07

## Decision: REJECTED

SPY's full-sample Sharpe (1.010) barely clears the 1.0 bar, but the
strategy fails on QQQ decisively, fails transaction-cost survival (net
Sharpe 0.424 < 0.5 threshold at a modest 10bps/trade assumption — this is a
mean-reversion strategy with meaningful turnover, ~63 trades over the
period), and fails parameter sensitivity (relative std 0.528, just over the
0.5 threshold) — the SPY-only pass looks like a fragile, cost-sensitive
near-miss rather than a robust edge. Crypto rejected outright (0/36).

Recorded as a near-miss (SPY headline Sharpe just above 1.0) worth a future
revisit with tighter trend/threshold tuning or a lower assumed cost basis,
but not accepted as-is.
