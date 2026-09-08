# Parkinson Volatility Expansion Trend Breakout — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_parkinson_vol_expansion_trend.py`
**Source:** TradingView "Parkinson Range Oscillator [BackQuant]" script
description (read via `browser_exec` after web_search failed with a
DuckDuckGo backend TLS error on this iteration's query; the direct TV
script page itself 404'd, but the Korean-locale mirror
`kr.tradingview.com/scripts/parkinson/` disclosed the full formula).

## Hypothesis

Parkinson volatility estimates realized variance from the intrabar
high-low range (`ln(H/L)`) rather than close-to-close returns:
`parkVol = sqrt(SMA(ln(H/L)^2, n) / (4*ln2)) * 100`, z-scored against its
own rolling baseline into an oscillator. First range-based realized-vol
estimator tested in this repo (distinct from Garman-Klass/ATR-based
constructs already covered). Hypothesis: an "expansion cross" (oscillator
crossing above its own EMA signal line while above-average-vol) combined
with an SMA trend filter marks a genuine acceleration of an existing
uptrend worth a long entry; a "compression cross" or trend break exits.

## Grid test (Step 6)

`park_window ∈ {5, 10, 20}` x `trend_window ∈ {50, 100}` x {QQQ, SPY,
BTC/USDT, ETH/USDT} x 3 vol terciles = 72 cells.

- **pass_fraction: 0.056** (4/72) — decisively weak
- by_asset_class: equity 4/36, crypto 0/36 (decisive fail)
- by_vol_regime: low 4/24 only, mid 0/24, high 0/24
- best_cell: QQQ, low-vol, `park_window=10, trend_window=50`, Sharpe 2.17 (narrow slice)

## Single-config validation (best config: `park_window=10, trend_window=50`)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.258 (FAIL, decisive) | 0.042 (FAIL, decisive) | ≥ 1.0 |
| Max drawdown | 0.165 (PASS) | 0.058 (PASS) | ≤ 0.25 |
| Net Sharpe after costs | 0.232 (FAIL) | 0.004 (FAIL) | ≥ 0.5 |

Trade counts: QQQ 11, SPY 6 (2019-01-01 to 2026-09-01) — very sparse
signal (expansion-cross + uptrend confirmation is a rare joint condition),
consistent with the grid's narrow low-vol-only pass concentration being a
small-sample artifact rather than a genuine edge.

## Decision: REJECTED (decisive)

Full-sample Sharpe collapses far below the 1.0 threshold on both equity
symbols (0.258 QQQ, 0.042 SPY — SPY is essentially flat/random), and
crypto fails all 36 grid cells. The grid's isolated best cell (Sharpe 2.17)
is a small-sample cherry-pick from only a handful of trades, not a robust
signal. The Parkinson-volatility-expansion-cross construction, at least
combined with a plain SMA trend filter as tested here, does not translate
into a tradeable edge on daily bars.
