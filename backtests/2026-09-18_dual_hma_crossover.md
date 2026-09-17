# Backtest Report: Dual HMA Crossover (2026-09-18)

**Hypothesis id:** 2026-09-18-057
**Strategy file:** `strategies/2026-09-18_dual_hma_crossover.py`
**Source:** https://quantifiedtrader.com/backtest/strategies/hull-ma-cross/ (fast HMA=9, slow HMA=18 disclosed default; `crossover(hma_fast, hma_slow)` entry, `crossover(hma_slow, hma_fast)` exit)

## Hypothesis

A fast Hull Moving Average crossing above a slow Hull Moving Average signals
a momentum-confirmed trend shift, entering faster than an SMA/EMA crossover
while remaining smoother than raw price. First two-HMA-line crossover tested
in this repo (existing entries only cover single-HMA-vs-price crossover and
single-HMA slope-turn).

## Step 6 grid summary (hma_fast in [6,9,12] x hma_slow in [18,26,36], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 108, passed_cells: 34, **pass_fraction: 0.315**
- by_asset_class: equity 23/54 (42.6%), crypto 11/54 (20.4%)
- by_vol_regime: low 25/36 (69.4%), mid 9/36 (25%), **high 0/36 (0%)**
- best_cell: hma_fast=6, hma_slow=36, QQQ, low-vol regime, Sharpe=1.979
- worst_cell: hma_fast=12, hma_slow=18, QQQ, high-vol regime, Sharpe=-0.450

Clear pattern: this strategy only works in low-realized-vol regimes; it
decisively fails in every high-vol cell across both asset classes. This
mirrors several other trend-following strategies already in this KB
(e.g. the BB mean-reversion QQQ strategy explicitly filters OUT high-vol
regimes for the same reason).

## Step 7 single-config validation (best cell params: hma_fast=6, hma_slow=36, QQQ, full 2019-2026 sample -- NOT vol-filtered)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.961 | >= 1.0 | **FAIL** (near-miss) |
| Max drawdown | 0.358 | <= 0.25 | **FAIL** |
| Transaction cost survival (15bps/trade, 113 trades) | net Sharpe 0.718 | >= 0.5 | PASS |
| Walk-forward | n/a | n/a | SKIPPED (pre-existing `vbt.utils.splitting` AttributeError bug in this repo's vectorbt version, consistent with prior entries e.g. 2026-09-18-055) |
| Parameter sensitivity (9-combo grid, QQQ full sample) | relative_std 0.244 | <= 0.5 | PASS |

The grid's best cell (Sharpe 1.979) is a **low-vol-regime-only** subset of
the sample; when run unconditionally over the FULL 2019-2026 QQQ sample
(including COVID crash and 2022 rate-hike drawdown, both high-vol
regimes), Sharpe drops to 0.961 (just under 1.0) and MDD blows out to
35.8% (exceeding the 25% cap) -- exactly the high-vol-regime failure the
grid predicted (0/36 high-vol cells passed).

## Decision: REJECT (unconditional form)

Sharpe and MDD both fail on the full, unconditional sample. The strategy
only has an edge inside low-vol regimes per the grid, so an unconditional
dual-HMA crossover is not viable as-is.

**Notes for a future iteration:** per the pattern of several prior
"rescue" chains in this KB (e.g. Mat Hold candlestick, BB mean-reversion),
a promising next step would be adding an explicit vol-regime gate (trade
only when realized vol <= its trailing median, matching what the grid
already shows works) rather than trading through all regimes
unconditionally -- this directly targets the demonstrated failure mode
(0/36 high-vol cells passing) instead of the crossover logic itself.
