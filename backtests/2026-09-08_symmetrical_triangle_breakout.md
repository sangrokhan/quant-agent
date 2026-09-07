# Symmetrical Triangle Breakout — QQQ/SPY/BTC/ETH

**Hypothesis:** Per https://finwiz.io/chart-patterns/symmetrical-triangle,
a symmetrical triangle forms with a descending upper trendline (lower
highs) and an ascending lower trendline (higher lows), volume declining
during formation and expanding on the breakout. Source's stated rule:
"Wait for a candle to close outside the triangle on strong volume... Enter
in the direction of the breakout," stop "below the most recent swing low
within the triangle," target "Breakout Price +/- Triangle Height (at
widest point)". First converging-trendline consolidation pattern in this
repo, built via OLS-fitted trendlines through confirmed swing highs/lows
rather than a fixed-width volatility band (distinct from Bollinger/BB-
Bandwidth squeeze constructions already tested).

Best config from grid search: `lookback_bars=25, contraction_ratio=0.7,
vol_expansion_mult=1.0` (pivot_window=4, min_pivots=2, max_hold_days=25,
target_mult=1.0 held fixed).

## Single-config validator results (best config)

| Validator | QQQ | SPY |
|---|---|---|
| sharpe_ratio | **FAIL** 0.364 (thr 1.0) | **FAIL** 0.589 (thr 1.0) |
| max_drawdown | pass 0.060 (thr 0.25) | pass 0.054 (thr 0.25) |
| transaction_cost_survival (10bps/trade, 2-6 trades) | **FAIL** 0.336 (thr 0.5) | pass 0.576 (thr 0.5) |

Trade counts are tiny (2-6 over 7.7 years) — the "valid triangle" state
(both trendlines fitted, contracting, correct slope signs) is rare on
daily bars, so the sample is thin and the low-MDD result mostly reflects
being flat almost all the time rather than genuine risk control.

## Step 6 grid summary (param_grid: lookback_bars∈{25,40},
contraction_ratio∈{0.7,0.85}, vol_expansion_mult∈{1.0,1.5}; symbols
QQQ/SPY (equity), BTC/USDT+ETH/USDT (crypto); vol_regime_splits=3)

- **pass_fraction: 0.0625** (6/96 cells)
- by_asset_class: equity 6/48 passed, **crypto 0/48 passed**
- by_vol_regime: low 4/32, mid 0/32, high 2/32 -- no coherent regime edge
- best_cell: QQQ, low-vol regime, Sharpe 1.10 (thin sample given overall
  trade scarcity)
- worst_cell: QQQ, high-vol regime, Sharpe -1.22

## Decision: REJECTED

Full-sample Sharpe fails decisively on both QQQ and SPY at the best grid
config, crypto shows zero edge across the entire 48-cell crypto grid, and
overall grid pass_fraction is very weak (0.0625) with no coherent
vol-regime pattern. Trade frequency is also too low (2-6 trades/7.7yr) for
the strategy to be practically meaningful even where it nominally "passes"
individual grid cells.

**Notes for future loops:** The OLS-fitted-trendline construction itself
(rather than the entry rule) may be the limiting factor -- daily-bar OHLC
swing points are noisy enough that a clean converging-triangle geometry is
rare. A future variant could try requiring fewer/looser pivot confirmation
(smaller pivot_window) or testing on higher-timeframe/weekly bars where
triangles are traditionally identified, rather than tweaking the current
daily-bar parameters further.
