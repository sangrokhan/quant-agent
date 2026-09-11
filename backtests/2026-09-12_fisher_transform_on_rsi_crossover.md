# Fisher Transform on RSI, signal-line crossover — Backtest Report

**Hypothesis:** Forward Fisher Transform applied to RSI (rescaled to [-1,1]),
smoothed, crossing its own SMA signal line, gated by close>SMA(trend_window).
Source: https://www.tradingview.com/script/AEVp3IFi-Fisher-Transform-on-RSI/
(PuzzlerTrades) + https://theindicatorlab.com/reviews/fisher-transform-indicator/
(corroborating smoothing/trend-filter guidance).

Distinct from prior repo entries: 2026-09-04-051 (Fisher on raw price),
2026-09-05-086 (Fisher on price + SMA gate), 2026-09-11-001 (Fisher on price,
slope-reversal), 2026-09-11-007/008 (Vervoort inverse-Fisher of a heavily
pre-smoothed RSI). This entry is the plain forward Fisher transform applied
directly to plain RSI, which is a novel combination in this repo.

## Best config (from grid): rsi_period=10, trend_window=100, max_hold_days=20

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.329 (FAIL, thr 1.0) | 0.141 (pass) | 0.156 (FAIL, thr 0.5) | 1.0 (pass) | 0.452 (pass) |
| SPY | 0.640 (FAIL, thr 1.0) | 0.122 (pass) | 0.352 (FAIL, thr 0.5) | 1.0 (pass) | 0.293 (pass) |

## Grid summary (rsi_period in {10,14,21} x trend_window in {50,100} x
max_hold_days in {15,20}, symbols QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- total_cells=144, passed_cells=23, pass_fraction=0.16
- by_asset_class: equity 23/72 passed, crypto 0/72 passed (decisive crypto reject)
- by_vol_regime: low 23/48, mid 0/48, high 0/48 (edge concentrated entirely in
  low-vol regime; fails everywhere else)
- best_cell: rsi_period=10/trend_window=100/max_hold_days=20, SPY, low-vol,
  Sharpe=1.50

## Verdict: REJECTED

Full-sample Sharpe and TC-survival both fail on QQQ and SPY despite passing
walk-forward and parameter sensitivity. The grid's apparent edge is entirely
a low-vol-tercile artifact (23/48 low vs 0/48 mid, 0/48 high) that does not
survive when averaged across the full sample. Crypto decisively rejected
(0/72). Not accepted; strategy file kept as a record of a tested/rejected
construction for future novelty checks.
