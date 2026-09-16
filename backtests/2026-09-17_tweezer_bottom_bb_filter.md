"""Backtest report: Tweezer Bottom candlestick + Bollinger Band filter (2026-09-17).

Source: https://www.quantifiedstrategies.com/tweezer-bottom-candlestick/
(visited via browser_exec -- web_search DDGS/Yahoo backend down with
RequestError/TLS errors on every query attempted this iteration). First
Tweezer Bottom entry in this repo (0 prior KB hits).

Pattern: two consecutive candles where the second candle's low revisits
the first candle's low without breaking it (within a small tolerance),
signaling bulls defending a key level after a bearish trend.

Rule (source's own disclosed "Trading Strategy 1"): tweezer bottom AND
close below the lower Bollinger Band (oversold mean-reversion filter) ->
long entry, exit after exit_bars (default 5) fixed hold.

## Grid summary (tolerance_pct in {0.002,0.005} x bb_std in {1.5,2.0,2.5}
x exit_bars in {3,5,8}, bb_window=20 fixed, QQQ+SPY+BTC/USDT+ETH/USDT,
vol_regime_splits=3)

- 216 cells total, 5 passed (2.3% pass_fraction) -- decisively weak
- by_asset_class: equity 5/108 (4.6%), crypto 0/108 (0%) -- crypto never
  passes a single cell
- by_vol_regime: low 0/72 (0%), mid 3/72 (4.2%), high 2/72 (2.8%)
- best config across grid: tolerance_pct=0.002/bb_std=1.5/exit_bars=3
  (2/12 cells, avg per-cell Sharpe only 0.067)
- best cell: tolerance_pct=0.002/bb_std=2.0/exit_bars=3, SPY mid-vol,
  Sharpe=1.66 (isolated outlier)
- worst cell: tolerance_pct=0.005/bb_std=2.0/exit_bars=8, SPY low-vol,
  Sharpe=-1.18

## Decision: REJECT (decisive grid rejection, no config approaches a
broadly viable Sharpe, crypto fails 0/108 outright; single-config
validator suite skipped since even the best full-grid-average config
(avg Sharpe 0.067) is far below the 1.0 threshold with no plausible fix
path).

The classic candlestick-double-bottom + Bollinger-oversold combination does
not produce a statistically robust edge on modern QQQ/SPY/BTC/ETH daily
bars at any tested parameterization -- consistent with the repo's several
other rejected candlestick-pattern + oscillator-confirmation combos.
"""
