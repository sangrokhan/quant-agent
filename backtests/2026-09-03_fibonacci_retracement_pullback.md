# Backtest report: Fibonacci retracement pullback-buy in uptrend

**Strategy file:** `strategies/2026-09-03_fibonacci_retracement_pullback.py`
**Hypothesis:** In an established uptrend (close > SMA200), buy pullbacks
that retrace 50%-61.8% (source's "preferred zone") to 78.6% (grid variant)
of the most recent swing-low-to-swing-high impulse move, exit on either a
new swing high (breakout resolved bullish) or a break below the swing low
("stop beyond the 100% retracement level"). Source:
https://www.quantifiedstrategies.com/fibonacci-trading-strategy/ (Oddmund
Groette). NOTE: the source itself carries an explicit documented negative
prior -- it cites Clarissa Gunawan's dissertation finding "the passive
trading strategy outperforms the active trading strategy using Fibonacci
retracements" on Vanguard ETFs, and states "we believe you're better off
using other strategies." This test independently checks the concrete rule
on this repo's QQQ/SPY/BTC/ETH universe anyway.

## Grid test (validation/grid_test.py::run_strategy_grid)

`swing_lookback` in {20,40} x `retrace_high` in {0.618,0.786} x
QQQ/SPY/BTC-USDT/ETH-USDT x 3 vol terciles, 48 cells, 2019-2026:

- pass_fraction: 0.125 (6/48) -- equity-only (6/24), crypto 0/24
- by_vol_regime: low 3/16, mid 2/16, high 1/16
- best_cell: SPY, swing_lookback=20/retrace_high=0.786, low-vol, Sharpe 1.41

## Standard validators (primary config: QQQ, swing_lookback=20, retrace_high=0.786)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.916 | 1.0 |
| max_drawdown | pass | 0.224 | 0.25 |
| transaction_cost_survival | pass | 0.872 (net Sharpe, 42 trades @10bps) | 0.5 |
| parameter_sensitivity | pass | rel.std 0.215 | 0.5 |

## Decision: REJECT (near-miss)

Sharpe is the only failing validator (0.916 vs 1.0 threshold, a 8%
shortfall) -- MDD, transaction-cost survival, and parameter sensitivity all
pass comfortably. This is a genuine near-miss, not a decisive rejection:
the Fibonacci 50-78.6% pullback-buy-in-uptrend rule shows real signal on
QQQ, just short of the Sharpe bar. Consistent with the source's own
documented skepticism (dissertation finding passive beats active
Fibonacci-retracement trading) but the magnitude of underperformance here
is small, not the wide gap the source's own caveat might suggest. Crypto
rejected (0/24 grid cells). A future loop could revisit with a tighter
retrace zone (closer to the literal 50-61.8% the source states as
"preferred" rather than the wider 0.786 upper bound used in this grid's
best cell) or a different swing-detection lookback to try to close the
remaining ~8% Sharpe gap.
