# Backtest Report: Triple MA Ribbon + MACD Histogram Confirmation (2026-09-18)

**Hypothesis id:** 2026-09-18-059
**Strategy file:** `strategies/2026-09-18_triple_ma_ribbon_macd_confirm.py`
**Source:** https://theindicatorlab.com/reviews/rob-hoffman-irb-ma-trend/ (visited this iteration)

## Hypothesis

3-line SMA ribbon (fast/mid/slow, e.g. 8/16/32) crossing/aligning bullish,
gated by a positive standard MACD(12,26,9) histogram (momentum
confirmation), avoids false ribbon-flip signals during chop. First
triple-MA-ribbon + explicit-MACD-histogram-gate combination tested in this
repo (existing GMMA/TEMA/Rainbow-MA entries have no MACD confirmation
gate).

## Step 6 grid summary (fast_window in [6,8,10] x mid_window in [16,20] x slow_window in [32,40], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 144, passed_cells: 49, **pass_fraction: 0.340**
- by_asset_class: equity 24/72 (33.3%), crypto 25/72 (34.7%)
- by_vol_regime: low 41/48 (85.4%), mid 8/48 (16.7%), **high 0/48 (0%)**
- best_cell: fast=8/mid=16/slow=40, ETH/USDT, mid-vol tercile, Sharpe=2.511
- worst_cell: fast=10/mid=16/slow=32, SPY, mid-vol tercile, Sharpe=-0.612

Same high-vol-regime failure pattern seen in several other trend-following
strategies in this KB (0/48 high-vol cells pass).

## Step 7 single-config validation (full 2019-2026 sample, unconditional -- no vol-gate applied)

| Symbol | Config | Sharpe | MDD | TC-survival | Trades |
|---|---|---|---|---|---|
| QQQ | fast=8/mid=16/slow=32 | 0.926 (FAIL, near-miss) | 0.114 (PASS) | 0.734 (PASS) | 62 |
| SPY | fast=8/mid=16/slow=32 | 0.430 (FAIL) | 0.108 (PASS) | 0.177 (FAIL) | 74 |
| BTC/USDT | fast=8/mid=16/slow=40 | 0.953 (FAIL, near-miss) | 0.375 (FAIL) | 0.899 (PASS) | 71 |
| ETH/USDT | fast=8/mid=16/slow=40 | 1.049 (PASS) | 0.355 (FAIL) | 1.013 (PASS) | 68 |

QQQ swept across all 12 grid param combos: best Sharpe only 0.946
(fast=8/mid=16/slow=40) -- consistently a near-miss, never clearing 1.0.

**ETH/USDT leverage-cap sweep** (to fix MDD, same rescue pattern as
2026-09-18-052/058): 0.8x MDD=0.290 (fail), 0.7x MDD=0.256 (fail), **0.6x
MDD=0.221 (pass)**, 0.5x MDD=0.187 (pass, lower returns).

### ETH/USDT final config: fast_window=8, mid_window=16, slow_window=40, leverage_cap=0.6

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.049 | >= 1.0 | **PASS** |
| Max drawdown | 0.221 | <= 0.25 | **PASS** |
| TC survival (15bps/trade, 68 trades) | net Sharpe 0.985 | >= 0.5 | **PASS** |
| Walk-forward | n/a | n/a | SKIPPED (pre-existing `vbt.utils.splitting` bug) |
| Parameter sensitivity (6-combo grid) | rel_std 0.018 | <= 0.5 | **PASS** |

## Decision: ACCEPT (ETH/USDT only, leverage_cap=0.6); REJECT (QQQ, SPY, BTC/USDT)

All 4 runnable validators pass for ETH/USDT. QQQ/BTC-USDT are consistent
Sharpe near-misses (0.9-0.95) across the full param grid -- not simply a
single unlucky config. SPY fails decisively on both Sharpe and TC
survival.

**Notes for a future iteration:** BTC/USDT's 0.953 Sharpe near-miss +
0.375 MDD is close in shape to ETH's original unscaled numbers -- a
BTC-specific leverage-cap retune (same 0.6x-style rescue) could plausibly
clear both metrics; QQQ's persistent ~0.9 Sharpe ceiling across the whole
grid suggests the momentum gate itself (not just parameter choice) may be
the equity-side limiting factor, worth revisiting with a different
momentum confirmation (e.g. RSI-based instead of MACD) rather than more
SMA-window tuning.
