# Relative Vigor Index (RVI) Signal-Line Crossover — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_rvi_signalline_cross.py`
**Source:** https://www.quantifiedstrategies.com/relative-vigor-index/
(exact numeric buy/sell trading rules and Amibroker code paywalled
members-only; web_search failed with a DDGS/Yahoo TLS connection error,
fell back to browser_exec)

## Hypothesis

The Relative Vigor Index (RVI) measures price momentum by comparing
close-to-open movement to the high-low trading range, smoothed with a
4-bar triangular (1:2:2:1) weighting kernel. Source's general rule: RVI
crossing above its own signal line (a further 4-bar weighted smoothing of
RVI) signals a bullish momentum shift. Source's own paywalled backtest
claims the strategy works on gold/crypto but explicitly NOT on SPY/TLT --
crypto was tested here as a genuine confirmation opportunity.

## Step 6 — Grid test summary

Grid: `rvi_window` in {10,14,20}, symbols {QQQ, SPY} (equity) x
{BTC/USDT, ETH/USDT} (crypto), vol_regime_splits=3.

- **total_cells:** 36, **passed_cells:** 8, **pass_fraction:** 0.222
- **by_asset_class:** equity 8/18, crypto 0/18
- **by_vol_regime:** low 6/12, mid 2/12, high 0/12
- **best_cell:** rvi_window=20, SPY, low-vol tercile, Sharpe 2.357
- **worst_cell:** rvi_window=10, QQQ, high-vol tercile, Sharpe -0.458

Full-sample sweep (3 windows x 2 symbols):

| Symbol | rvi_window | Sharpe | MDD | Trades |
|---|---|---|---|---|
| QQQ | 10 | 0.384 | 0.414 | 357 |
| QQQ | 14 | 0.406 | 0.350 | 351 |
| QQQ | 20 | 0.432 | 0.323 | 352 |
| SPY | 10 | -0.046 | 0.332 | 365 |
| SPY | 14 | 0.113 | 0.335 | 359 |
| SPY | 20 | 0.180 | 0.302 | 348 |

All 6 full-sample results are weak-to-negative (-0.046 to 0.432),
decisively below the 1.0 threshold with no near-miss, and MDDs (0.30-0.41)
would fail even if Sharpe passed. Very high trade frequency (~350 trades
over 7.7yr) at this daily-bar RVI signal-line cross likely generates
excessive whipsaw. Skipped remaining validator suite per Step 7
minimum-subset guidance.

## Decision

**Rejected (all asset classes).** Full-sample Sharpe never exceeds 0.432
across 6 combo/symbol pairs on equity, with elevated max drawdowns
(0.30-0.41). Crypto rejected decisively (0/18 grid cells) -- notably this
does NOT confirm the source's own claim of RVI effectiveness in crypto
trading, worth recording as a specific falsification of that claim on
this repo's BTC/ETH daily-bar sample.
