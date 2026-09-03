# Backtest report: RSI bullish divergence, long-only

**Strategy file:** `strategies/2026-09-03_rsi_bullish_divergence.py`
**Hypothesis:** Bullish RSI(14) divergence between successive local swing
lows (price makes lower low, RSI makes higher low, first swing low's RSI
<30) signals seller-momentum exhaustion -> long entry, exit on RSI crossing
back above 50 or after `max_hold_days`. Source:
https://backtestx.in/guide/backtesting-rsi -- concrete codified rules
quoted: "RSI must be in oversold (below 30) ... during the first swing
peak. Price must make a clear second peak/trough outside the previous
boundaries. RSI second peak must be visually higher (for bullish) ... than
the first." Source's own FX backtest found ~48-52% win rate in
range-bound markets, <35% in trends -- flagged as a caveat here.

## Grid test (validation/grid_test.py::run_strategy_grid)

`oversold_threshold` in {25,30,35} x `max_hold_days` in {10,15} x
QQQ/SPY/BTC-USDT/ETH-USDT x 3 vol terciles, 72 cells, 2019-2026:

- **pass_fraction: 0.097** (7/72) -- weakest of any strategy tested this trigger
- by_asset_class: equity 7/36, crypto 0/36
- by_vol_regime: low 0/24, mid 4/24, high 3/24
- best_cell: SPY, oversold=30/max_hold=10, mid-vol tercile, Sharpe 1.40

## Full-sample check at grid-optimal config (oversold_threshold=30, max_hold_days=10)

| symbol | full-sample Sharpe | nonzero days |
|---|---|---|
| QQQ | 0.05 | 28 |
| SPY | 0.58 | 33 |
| BTC/USDT | 0.44 | 1804 |

The grid's "best cell" (SPY mid-vol, Sharpe 1.40) is a narrow-slice
artifact: the full 2019-2026 sample at the same config gives QQQ a Sharpe
of essentially zero (0.05) and SPY only 0.58 -- nowhere near the 1.0
threshold. Extremely low trade count (QQQ: only 3 completed round trips
over 7.7 years) makes any single-slice result statistically unreliable.

## Standard validators (primary config: QQQ, oversold=30, max_hold=10)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.050 | 1.0 |
| max_drawdown | pass | 0.098 | 0.25 |
| transaction_cost_survival | **FAIL** | 0.041 (net Sharpe) | 0.5 |
| walk_forward | not run (vectorbt.utils.splitting API bug, same as every prior iteration this log) | - | - |
| parameter_sensitivity | not run (already 2/3 core validators fail decisively) | - | - |

## Decision: REJECT

Sharpe and transaction-cost-survival both fail decisively at the
grid-optimal full-sample config on QQQ (0.05 and 0.04 respectively, vs 1.0
and 0.5 thresholds). The extremely low signal frequency (single-digit
completed trades per symbol over 7.7 years) makes the swing-pivot
divergence detector, as implemented with a simple centered-window local-min
finder, too rare/noisy an edge to validate reliably -- consistent with the
source's own caveat that raw RSI divergence performs poorly outside
range-bound regimes and needs a higher-timeframe trend filter to be useful
(not implemented here). Crypto also rejected (0/36 grid cells). A future
loop could revisit with a proper trend/support-zone filter on top of the
divergence trigger, or a looser swing-detection window to generate more
signal frequency for a statistically meaningful sample.
