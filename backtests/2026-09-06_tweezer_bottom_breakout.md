# Tweezer Bottom Breakout Strategy — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_tweezer_bottom_breakout.py`
**Source:** https://www.mnclgroup.com/tweezer-bottom-candlestick-pattern-guide

## Hypothesis

Tweezer Bottom (two consecutive candles with nearly-identical lows,
occurring in a downtrend) signals weakening downside momentum. Source's own
"Breakout Confirmation Strategy": wait for price to move above the
pattern's high after detection, then enter long; exit below the pattern's
low or a time-stop.

## Single-config validator results (tweezer_tolerance_pct=0.003, trend_window=50)

| Symbol | Sharpe | Threshold | Pass | Max DD | Threshold | Pass |
|---|---|---|---|---|---|---|
| QQQ | 0.435 | 1.0 | FAIL | 0.222 | 0.25 | PASS |
| SPY | 0.315 | 1.0 | FAIL | 0.146 | 0.25 | PASS |

Decisive Sharpe failure on both equity tickers -- the pattern is common
enough (272-316 trading days with exposure over ~7.5 years) to generate a
sizable sample, but the edge is too weak/noisy to clear the risk-adjusted
bar.

## Grid test summary

`param_grid={"tweezer_tolerance_pct": [0.002, 0.003, 0.005], "trend_window": [50, 200]}`,
symbols equity=[QQQ, SPY] crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.069 (5/72 cells)**
- by_asset_class: equity 5/36 passed; crypto 0/36 passed (decisive reject for crypto)
- by_vol_regime: low 1/24, mid 3/24, high 1/24
- best_cell: tweezer_tolerance_pct=0.003, trend_window=50, QQQ, mid-vol, Sharpe 1.24
- worst_cell: same params, QQQ, low-vol, Sharpe -1.10 (same config swings from best to worst cell across vol regimes -- highly regime-dependent, not a robust edge)

## Decision: REJECTED

Full-sample Sharpe fails decisively on both QQQ (0.435) and SPY (0.315);
grid pass_fraction (6.9%) confirms this isn't a parameterization artifact,
and the fact that the identical best-performing parameter combo swings from
Sharpe +1.24 (mid-vol) to -1.10 (low-vol) on the same symbol shows the
signal is highly regime-dependent noise rather than a consistent edge.
Crypto rejected outright (0/36).

Walk-forward / transaction-cost / parameter-sensitivity validators skipped
(decisive full-sample + grid failure already settles this).
