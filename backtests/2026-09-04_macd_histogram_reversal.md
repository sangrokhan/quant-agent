# Backtest Report: MACD Histogram Momentum Reversal (mean-reversion)

**Strategy file:** `strategies/2026-09-04_macd_histogram_reversal.py`
**Date:** 2026-09-04
**Source:** https://www.quantifiedstrategies.com/macd-histogram/
(retrieved via browser_exec after web_search DDGS/Yahoo TLS failure)

## Hypothesis

MACD histogram below zero AND turning from falling to rising (inflection)
signals a bottoming/reversal-up worth a long entry; exit on the first day
close > prior close (source's stated free exit rule).

## Grid test summary (require_uptrend x max_hold_days x 4 symbols x 3 vol terciles = 48 cells)

- pass_fraction: **8.3%** (4/48) -- weak, concentrated entirely in
  equity/low-vol cells
- by_asset_class: equity 4/24 (17%), crypto 0/24 (0%)
- by_vol_regime: low 4/16, mid 0/16, high 0/16
- best_cell: QQQ, require_uptrend=True/max_hold_days=10, low-vol, Sharpe 1.15

## Full-sample single-config metrics

| Symbol | require_uptrend | Sharpe | Pass | MDD   | Pass | Trades |
|--------|------------------|--------|------|-------|------|--------|
| SPY    | False            | 0.061  | No   | 0.191 | Yes  | 266    |
| SPY    | True             | 0.546  | No   | 0.074 | Yes  | 176    |
| QQQ    | False            | -0.345 | No   | 0.327 | No   | 270    |
| QQQ    | True             | -0.028 | No   | 0.206 | Yes  | 186    |

## Decision: REJECTED

No configuration on either equity symbol comes close to the Sharpe
threshold at full-sample (best: SPY with the optional 200d trend filter at
0.546); without the trend filter SPY is essentially flat/no-edge (0.06) and
QQQ is negative. Crypto is a complete washout in the grid (0/24 cells).
Consistent with the source's own framing of this as one of many candidate
"Core MACD Histogram Strategies" variants (Momentum Reversal, Expansion,
Zero-Line Crossover, Divergence) rather than a singularly strong signal --
the specific numeric entry threshold in the source's own paywalled backtest
may differ meaningfully from the free "Core Strategies" description
implemented here (e.g. requiring a minimum inflection magnitude, not just
any 1-day directional flip, which would filter much of the noise this
simple version trades on).
