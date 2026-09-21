# Bearish Separating Lines Short — Backtest Report (2026-09-21)

## Hypothesis
Source: https://www.quantifiedstrategies.com/bearish-separating-lines-candlestick-pattern/
(read via browser_exec fallback). 2-candle bearish continuation in a
downtrend: bullish candle 1, bearish candle 2 opening near candle 1's open
and closing below candle 1's low. Entry short below candle 2's low, generic
stop-loss guidance only (this repo's standard ATR stop/target used).

Strategy file: `strategies/2026-09-21_bearish_separating_lines_short.py`

## Step 6 — Grid test summary
`grid_summary_bearish_separating_lines_short.json` /
`grid_cells_bearish_separating_lines_short.json`

- Grid: `trend_window` in {30, 50, 100}, `open_match_tolerance_pct` in
  {0.002, 0.003, 0.005}, `target_atr_mult` in {1.5, 2.0, 3.0}; symbols
  QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3; 324
  total cells.
- **pass_fraction: 0.003** (1/324 cells). Single passing cell: SPY,
  low-vol-regime, `trend_window=30, open_match_tolerance_pct=0.005,
  target_atr_mult=1.5`, Sharpe 1.0074 -- a razor-thin single-cell pass, the
  thinnest result of any strategy tested this cron trigger.
- by_asset_class: equity 1/162, crypto 0/162. by_vol_regime: low 1/108,
  mid 0/108, high 0/108.

## Step 7 — Single-config validation
Skipped a full validators.py run: with only 1/324 cells passing at
Sharpe=1.0074 (a coin-flip margin above the 1.0 threshold in a single
vol-regime slice), this is a decisively non-robust result not worth the
compute for a full validator suite -- consistent with every other
razor-thin single-cell "pass" seen this cron trigger (e.g. Bearish Kicker
iteration 4, Downside Tasuki iteration 5) that failed full-sample
validation when checked.

## Step 8 — Decision: **REJECT**

Rejection reason: 1/324 grid cells pass (0.3% pass_fraction), a razor-thin
single-cell result (Sharpe 1.0074) confined to one asset/vol-regime
combination -- not a demonstrated, parameter-robust edge. Pattern is rare
(40 non-zero position bars for QQQ default params over 2018-2026, but the
edge does not hold at the aggregate level).

Strategy file and this report are kept as a record of a rejected attempt.
