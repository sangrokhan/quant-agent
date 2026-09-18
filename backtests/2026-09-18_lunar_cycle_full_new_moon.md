# 2026-09-18-067: Lunar Cycle (Full Moon / New Moon) Seasonal Timing

## Hypothesis

Per Yuan, Zheng & Zhu (2006, "Are Investors Moonstruck?") and the
QuantifiedStrategies.com summary/backtest read this iteration
(https://www.quantifiedstrategies.com/full-moon-moon-phases-lunar-cycles-trading-strategies/),
stock index returns are systematically lower around full-moon days and
higher around new-moon days, a documented lunar-cycle seasonal anomaly. Two
source-stated variants tested: `full_to_new` (long full-moon->new-moon) and
`new_to_full` (long new-moon->full-moon). Moon phase computed via the
standard synodic-month approximation (reference new moon 2000-01-06 18:14
UTC + 29.53058867-day synodic period), no external astronomy library
required.

Source: https://www.quantifiedstrategies.com/full-moon-moon-phases-lunar-cycles-trading-strategies/
(also references academic study Yuan/Zheng/Zhu 2006).

First lunar-cycle / moon-phase strategy in this repo.

## Step 6 grid summary

`param_grid={phase_variant: [full_to_new, new_to_full], new_moon_window:
[1.0, 1.5], full_moon_window: [1.0, 1.5]}`, `symbols={equity: [QQQ, SPY],
crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`, 2018-01-01..2026-09-01.

- total_cells=96, passed_cells=24, pass_fraction=0.25
- by_asset_class: equity 22/48, crypto 2/48 (decisively equity-only)
- by_vol_regime: low 18/32, mid 4/32, high 2/32 (edge concentrated in
  low-vol regimes, consistent with a mood/behavioral seasonal effect being
  swamped by macro/vol-driven moves in turbulent periods)
- best_cell: `full_to_new`, new_moon_window=1.0, full_moon_window=1.5, SPY,
  low-vol regime, Sharpe 2.34
- worst_cell: `new_to_full`, new_moon_window=1.0, full_moon_window=1.5, QQQ,
  high-vol regime, Sharpe -0.93
- Best average-across-vol-regimes config per symbol: SPY `full_to_new`
  (new_moon_window=1.0, full_moon_window=1.5) avg Sharpe 1.177, pass 2/3
  vol regimes; QQQ same variant/params avg Sharpe 1.161, pass 1/3.
- crypto (BTC/USDT, ETH/USDT) never passed under `full_to_new`; only
  marginal passes (1/3) for BTC/USDT under `new_to_full`.

## Single-config validation (SPY, full_to_new, new_moon_window=1.0,
full_moon_window=1.5, 2018-01-01..2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.964 | 1.0 | **fail** |
| Max drawdown | 0.227 | 0.25 | pass |
| Net Sharpe after costs (10bps/trade, 174 trades) | 0.747 | 0.5 | pass |
| Walk-forward (4 equal splits, manual substitute*, positive-Sharpe fraction) | 1.00 (4/4) | 0.75 | pass |
| Parameter sensitivity (relative std across 8-combo grid, SPY) | 0.300 | 0.5 | pass |

\* `validation/validators.py::check_walk_forward` errors on the installed
vectorbt 1.1.0 (`module 'vectorbt.utils' has no attribute 'splitting'`) --
substituted a manual 4-equal-contiguous-split walk-forward with the
identical pass criterion, matching the established fallback pattern (see
`backtests/2026-09-18_bullish_pin_bar_support_reversal.md`).

## Decision

**Rejected.** Full-sample Sharpe (0.964) narrowly misses the 1.0 threshold
despite the grid's best single-vol-regime cell (SPY low-vol, 2.34) looking
strong, and despite every other validator (MDD, transaction-cost survival,
walk-forward, parameter sensitivity) passing cleanly. This is a genuine
near-miss worth flagging for a future iteration: the edge is real and
narrow-but-honest on equity/low-vol only (grid pass_fraction 0.25 overall,
concentrated 18/32 in low-vol), crypto is decisively rejected across the
board. A future loop could retune `new_moon_window`/`full_moon_window`
tighter, or add a low-vol-regime gate on top (similar to this repo's
established vol-regime-gate pattern) to push the full-sample Sharpe over
1.0 by excluding the high/mid-vol drag periods explicitly rather than
averaging over them.
