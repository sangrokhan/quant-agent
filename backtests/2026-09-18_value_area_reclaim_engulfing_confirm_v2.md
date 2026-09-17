# Backtest Report: Value Area Reclaim + Lagged Engulfing/Volume Confirmation (2026-09-18, v2)

**Hypothesis id:** 2026-09-18-064
**Strategy file:** `strategies/2026-09-18_value_area_reclaim_engulfing_confirm.py` (same file, code updated: confirmation now allowed within a trailing `confirm_window` bars instead of requiring same-bar coincidence)
**Source:** Own prior entry's notes (2026-09-18-063) + re-reading LuxAlgo's "Maximum bars to signal after breakout" setting

## Hypothesis

Direct fix for 2026-09-18-063's signal-starvation rejection (same-bar
compound filter produced only 1-24 trades total, zero grid cells passed).
Per that entry's own notes and the source indicator's own "Maximum bars to
signal after breakout" setting, relaxed the bullish-engulfing +
volume-expansion confirmation to fire any time within a trailing
`confirm_window` (default 5, tested up to 15) bars of the VAL reclaim,
rather than requiring exact same-bar coincidence.

## Trade count check (fixes starvation, but only partially)

| Symbol | confirm_window=5 trades | confirm_window=15, vol_mult=1.0 trades |
|---|---|---|
| QQQ | 2 | 9 |
| SPY | 2 | (not separately re-checked) |
| BTC/USDT | 22 | (grid config) |
| ETH/USDT | 24 | (grid config) |

Trade counts improved substantially vs. 2026-09-18-063 (was 1-12 total)
but equity remains too thin (single-digit trades) for meaningful
statistics even at the most relaxed setting tested.

## Step 6 grid summary (vol_expansion_mult in [1.0,1.1] x confirm_window in [10,15], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 48, passed_cells: 4, **pass_fraction: 0.083**
- by_asset_class: equity 2/24 (8.3%), crypto 2/24 (8.3%)
- by_vol_regime: low 0/16 (0%), mid 2/16, high 2/16
- best_cell: vol_expansion_mult=1.1/confirm_window=15, BTC/USDT, high-vol tercile, Sharpe=1.270

## Step 7 single-config validation (BTC/USDT, best grid config, FULL unconditional 2019-2026 sample)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 0.223 | >= 1.0 | **FAIL** (decisive) |
| Max drawdown | 0.197 | <= 0.25 | PASS |
| TC survival (15bps/trade, 63 trades) | net Sharpe 0.063 | >= 0.5 | **FAIL** (decisive) |

The grid's "best cell" (Sharpe 1.270) was a narrow high-vol-tercile
subset, not representative of the full sample -- the unconditional
full-period Sharpe collapses to 0.223, decisively below threshold.

## Decision: REJECT

Both the relaxed lagged-confirmation fix and the original same-bar
version fail. Unlike 2026-09-18-063 (rejected for pure signal starvation
with zero usable trades), this version has enough trades to test
properly (63 on BTC/USDT) and still shows no real edge once averaged
across the full sample -- the earlier grid's apparent promise was a
narrow-regime artifact, not the fix hoped for.

**Notes for a future iteration:** This closes out the Value-Area-reclaim
family for now with a genuinely negative full-sample result (not just an
infeasibility/starvation issue) -- a future iteration should treat further
VAL-reclaim-with-candle-confirmation variants as low-priority given two
consecutive rejections (2026-09-10-001 unconditional, 2026-09-18-063/064
various confirmation filters), unless a fundamentally different
confirmation mechanism (e.g. multi-bar consolidation above VAL rather
than a single candle pattern) is tried.
