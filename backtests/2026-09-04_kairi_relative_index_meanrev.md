# Kairi Relative Index (KRI) mean-reversion pullback, trend-gated — REJECTED

**Hypothesis:** KRI (100*(close-SMA)/SMA) dropping to/below an oversold
threshold, gated by close > SMA(200) uptrend filter, marks a mean-reversion
long entry. Source: https://www.quantifiedstrategies.com/kairi-relative-index/

**Grid test** (`validation/grid_test.py::run_strategy_grid`):
sma_window=[20,26,34] x entry_threshold=[-10,-7] x trend_window=[200] x
max_hold_days=[10,15], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT
(crypto), vol_regime_splits=3, 2018-01-01..2026-09-01.

- total_cells: 96, passed_cells: 0, **pass_fraction: 0.0%**
- by_asset_class: equity 0/72, crypto 0/24
- by_vol_regime: low 0/24, mid 0/24, high 0/24, n/a 0/24
- best_cell: QQQ, sma_window=34, entry_threshold=-7.0, max_hold_days=10,
  high-vol regime, Sharpe=0.409 (still below min_sharpe=1.0)
- worst_cell: QQQ, sma_window=20, entry_threshold=-7.0, high-vol regime,
  Sharpe=-0.049

**Single-config validator confirmation** (best cell params, QQQ,
2018-01-01..2026-09-01):
- Sharpe ratio: **FAIL** (0.235 vs threshold 1.0)
- Max drawdown: PASS (0.187 vs threshold 0.25)

**Decision: REJECT.** Decisive — 0/96 grid cells passed, best cell Sharpe
well below threshold across all asset classes and vol regimes. Trend-gated
oversold-KRI pullback does not produce an edge in this repo's daily-bar
QQQ/SPY/BTC/ETH universe.
