# Backtest Report: Fibonacci Pivot Point Breakout (QQQ)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_fibonacci_pivot_breakout.py`
**Source:** https://quantengines.com/blog/pivot-point-trading-strategy (read via browser_exec; web_extract failed — ddgs backend is search-only)

## Hypothesis
Fibonacci pivot levels (PP + 0.382/0.618/1.0 x prior-period range) are
widely-watched intraday support/resistance. Per the source article's
"Trading Strategy 2: Pivot Breakout" section, a close beyond R1 tends to
continue toward R2/R3, with the broken level acting as new support.
Adapted to daily bars (repo has no intraday data): long when today's close
> R1 computed from yesterday's H/L/C; exit when close < PP or after
`max_hold_days`.

## Single-config validators (QQQ, fib_r1=0.618, max_hold_days=10 — grid's best cell)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | **FAIL** | 0.349 | >= 1.0 |
| Max drawdown (full sample) | **FAIL** | 0.358 | <= 0.25 |
| Transaction cost survival (10bps/trade, 297 trades) | **FAIL** | net Sharpe 0.004 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | known repo `vectorbt.utils.splitting` AttributeError bug, light workload |
| Parameter sensitivity (from grid, 4 combos) | PASS | rel_std 0.0498 | <= 0.5 |

## Grid summary (Step 6)
`param_grid={"fib_r1": [0.382, 0.618], "max_hold_days": [5, 10]}`,
`symbols={"equity": ["QQQ", "SPY"]}`, `vol_regime_splits=3` (light workload, equity only).

- total_cells: 24, passed_cells: 12, **pass_fraction: 0.5**
- by_vol_regime: low 8/8 PASS, mid 4/8 PASS, **high 0/8 FAIL**
- best_cell: fib_r1=0.618, max_hold_days=10, SPY, low-vol, Sharpe 2.49
- worst_cell: same params, SPY, high-vol, Sharpe -0.84

## Interpretation
The edge is real but entirely concentrated in low/mid realized-vol regimes;
during high-vol regimes the strategy decisively loses money (Sharpe
consistently negative). Since the full-sample metrics (which any live
deployment would be exposed to across all regimes) fail Sharpe/MDD/TC-survival
outright, and the repo's grid-based regime detection is not wired into
`generate_signals`/`generate_returns` as a live filter (the strategy has no
volatility-regime gate of its own — Step 5 code doesn't condition entries on
realized vol), this is a **reject** at the whole-sample level. A future
iteration could revisit this as a "regime-gated Fibonacci pivot breakout"
(add a low/mid-vol-only entry filter, following the same pattern as
`2026-09-03_bb_meanrev_qqq_volregime.py`) rather than as a fresh idea.

## Decision: REJECT (QQQ, full sample)
Files kept in `strategies/`/`backtests/` as a record of a rejected attempt —
not a live strategy.
