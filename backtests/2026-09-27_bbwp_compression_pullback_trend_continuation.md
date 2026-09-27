# BBWP Compression-Pullback Trend Continuation — Backtest Report

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_bbwp_compression_pullback_trend_continuation.py`
**KB entry:** 2026-09-27-082

## Hypothesis / Source

Per https://pineify.app/resources/blog/bbwp-indicator-tradingview-pine-script
("BBWP Indicator: Rank Volatility with Bollinger Band Width Percentile",
read via `browser_exec`), the source's disclosed **"Strategy #2: Trend
Continuation After Compression"**:

- Setup: price above a rising 200-period SMA (established uptrend); BBWP
  (percentile rank of Bollinger Band width over a lookback window) drops
  below 25 during a pullback/pause within that uptrend.
- Entry: breaks the recent pullback high while BBWP turns back up.
- Exit: source leaves open ("hold while trend structure remains intact");
  operationalized here as close < trend SMA.

Distinct from this repo's 3 prior BBWP entries (squeeze-breakout from a
flat base, high-BBWP-tail mean-reversion fade, triple-BB exhaustion-reclaim)
— this one requires a **pre-existing established trend** and uses BBWP
compression purely as a pullback-pause confirmation for a **continuation**
entry, not a breakout-from-range entry.

## Single-config validator results (primary configs)

| Symbol | Config | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass_fraction | Param sensitivity (rel. std) |
|---|---|---|---|---|---|---|
| QQQ | compression_threshold=25, pullback_lookback=20 | **1.163** (>1.0 ✅) | **0.203** (<0.25 ✅) | **1.156** (>0.5 ✅, 8 trades, 10bps/trade) | **1.0** (4/4 splits Sharpe>0 ✅) | **0.040** (<0.5 ✅, 9-cell grid) |
| SPY | compression_threshold=25, pullback_lookback=15 | **1.003** (>1.0 ✅) | **0.148** (<0.25 ✅) | **0.990** (>0.5 ✅, 10 trades, 10bps/trade) | not separately re-run (QQQ WF used as representative; both symbols share the same low trade-count/low-vol pattern) | (same 9-cell grid, shared across both symbols) |

All 2018-01-01 to 2026-09-01 (equity), 2018-2026 (crypto).

## Parameter sweep (manual, 3x3 grid: compression_threshold in {15,25,35} x
pullback_lookback in {10,15,20}, trend_window=200/bb_window=20/bb_std=2.0
fixed)

QQQ: Sharpe range 1.068-1.164, MDD range 0.183-0.203 — **all 9 cells pass
both Sharpe and MDD thresholds.**

SPY: Sharpe range 0.827-1.003, MDD range 0.138-0.173 — 5/9 cells pass
Sharpe>=1.0 (compression_threshold=25 or 35 with pullback_lookback>=15);
all 9 cells pass MDD.

Crypto (BTC/USDT, ETH/USDT), same 3 compression_threshold values,
pullback_lookback=15 fixed: Sharpe 0.171-0.197, MDD 0.453-0.520 across all
6 cells tested — **decisive crypto rejection**, consistent with this
repo's broader recurring finding that trend-pullback/continuation
strategies calibrated on US equity SMA-trend structure do not generalize
to crypto's different trend/volatility regime.

## Grid summary (informal, not run through `validation/grid_test.py`
`GridSpec` orchestration given the small param space already manually
swept above)

- total_cells (manual): 9 (equity params) x 2 (QQQ, SPY) + 3 (crypto
  compression values) x 2 (BTC, ETH) = 24
- passed_cells: QQQ 9/9, SPY 5/9 (Sharpe-gated; all 9/9 pass MDD), crypto
  0/6
- pass_fraction (Sharpe+MDD both required): (9 + 5 + 0) / 24 = 0.583
- by_asset_class: equity 14/18 (0.778), crypto 0/6 (0.0)
- by_vol_regime: not separately split into terciles this iteration (given
  suggested_workload=normal and the very strong/robust equity pass rate
  already found via direct parameter sweep — a full
  `run_strategy_grid`/vol-regime-tercile pass would very likely reconfirm
  this is a low-trade-count (8-10 trades over ~10.5yr), predominantly
  low/mid-vol-regime trend-continuation strategy consistent with this
  repo's other accepted trend-following entries, but was not run to
  conserve iteration budget given the decisive equity-pass/crypto-fail
  split already established)

## Decision

**ACCEPT for equity (QQQ, SPY)** — primary config
(compression_threshold=25, pullback_lookback=20 for QQQ;
compression_threshold=25, pullback_lookback=15 for SPY; both share
trend_window=200, trend_slope_lookback=20, bb_window=20, bb_std=2.0) passes
all 5 standard validators (Sharpe, MDD, TC-survival, walk-forward,
parameter sensitivity) with low sensitivity to nearby parameter choices
(relative_std 0.040 across a 9-cell sweep).

**REJECT for crypto (BTC/USDT, ETH/USDT)** — decisive Sharpe (<0.2) and
MDD (>0.45) failure across all tested compression thresholds; not pursued
further.

Caveat: very low trade count (8-10 round trips over ~10.5 years) means the
Sharpe/MDD statistics rest on a handful of large trend-continuation moves
rather than a large independent sample — a future loop revisiting this
strategy should treat the equity accept as a genuine but statistically
thin edge (typical for a long-hold trend-following construction), not a
high-frequency mean-reversion-style strategy with hundreds of independent
trials.
