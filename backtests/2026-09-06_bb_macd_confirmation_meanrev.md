# Bollinger Band + MACD Confirmation Mean-Reversion Strategy — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_bb_macd_confirmation_meanrev.py`
**Source:** https://www.luxalgo.com/blog/bollinger-bands-and-macd-entry-rules-explained/

## Hypothesis

Per LuxAlgo's guide, a long entry requires ALL of: price touching/nearing
the lower Bollinger Band, a MACD bullish line/signal crossover, MACD
histogram above zero, and price starting to bounce upward -- combining
volatility-extreme and momentum-confirmation signals should reduce false
mean-reversion entries versus either indicator alone.

## Single-config validator results (bb_std=2.0, touch_lookback=3, default params)

| Symbol | Sharpe | Trades | Note |
|---|---|---|---|
| QQQ | inf (undefined) | 0 | Zero trades over full 2019-2026 sample |
| SPY | inf (undefined) | 0 | Zero trades over full 2019-2026 sample |

The four-condition conjunction (lower-band touch AND MACD bullish crossover
AND histogram>0 AND same-day price bounce) is so restrictive that it never
co-occurs on the same bar over the full ~7.5-year daily-bar sample for
either primary equity ticker -- the signal is not just weak, it's
effectively non-existent at these default settings.

## Grid test summary

`param_grid={"bb_std": [1.5, 2.0, 2.5], "touch_lookback": [1, 3, 5]}`,
symbols equity=[QQQ, SPY] crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.009 (1/108 cells)** -- the lowest pass fraction of any
  strategy tested in this repo to date.
- by_asset_class: equity 1/54 passed; crypto 0/54 passed (decisive reject for crypto)
- by_vol_regime: low 0/36, mid 1/36, high 0/36
- best_cell: bb_std=2.0, touch_lookback=5 (the loosest lookback tested), SPY, mid-vol, Sharpe 1.02 -- a single passing cell, likely driven by a very small number of trades in that narrow slice.
- worst_cell: same params, QQQ, high-vol, Sharpe -0.69

Even the loosest touch_lookback=5 setting only produces one passing cell
out of 108 -- the conjunction of four independent technical conditions is
simply too restrictive to generate a usable, non-sparse trading signal on
daily bars.

## Decision: REJECTED

Zero trades at the source's own recommended default parameterization on
both primary equity tickers over the full sample; grid pass_fraction (0.9%)
is the most decisive rejection recorded in this repo to date. The
underlying issue is signal SPARSITY, not poor risk-adjusted performance --
requiring four independent conditions (band touch + MACD crossover +
histogram sign + same-day bounce) to align simultaneously is too
restrictive for daily bars. A looser variant (e.g. requiring conditions
within a tolerance window rather than the same bar) might be worth
revisiting in a future iteration, but is out of scope here.

Walk-forward / transaction-cost / parameter-sensitivity validators skipped
(zero-trade full-sample result already settles this decisively).
