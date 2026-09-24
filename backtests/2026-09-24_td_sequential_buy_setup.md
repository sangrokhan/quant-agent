# Backtest Report: TD Sequential Bullish 9-count Buy Setup (QQQ)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_td_sequential_buy_setup.py`
**Source:** https://trendspider.com/learning-center/td-sequential-a-comprehensive-guide-for-traders/ (browser_exec; web_extract failed — ddgs backend search-only)

## Hypothesis
TD Sequential (Tom DeMark) TD Buy Setup: an unbroken streak of 9 consecutive
closes each below the close 4 bars earlier signals a trend-exhausted
downtrend, a potential reversal point. Long entry on setup completion;
exit on a new low below the setup bar's low (stop) or a break above the
setup close by a small buffer (target), or a max-hold time-stop. First TD
Sequential/DeMark strategy in this repo (0 prior hits) — implements only
the simpler 9-bar Setup phase, not the more complex 13-bar Countdown phase.

## Single-config validators (QQQ, max_hold_days=5, stop_buffer_pct=0.01 — grid's best cell)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | **FAIL** | 0.336 | >= 1.0 |
| Max drawdown | PASS | 0.056 | <= 0.25 |
| Transaction cost survival (10bps, 16 trades) | **FAIL** | net Sharpe 0.277 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | known repo `vectorbt.utils.splitting` bug, light workload |
| Parameter sensitivity (from grid, 4 combos) | **FAIL** | rel_std 1.428 | <= 0.5 |

## Grid summary (Step 6)
`param_grid={"max_hold_days": [5, 10], "stop_buffer_pct": [0.01, 0.02]}`,
`symbols={"equity": ["QQQ", "SPY"]}`, `vol_regime_splits=3` (light workload).

- total_cells: 24, passed_cells: 0, **pass_fraction: 0.0**
- by_vol_regime: low 0/8, mid 0/8, high 0/8 (all fail)
- best_cell: max_hold_days=5, stop_buffer_pct=0.01, QQQ, high-vol, Sharpe 0.867
- worst_cell: same params, SPY, low-vol, Sharpe -1.078

## Decision: REJECT (QQQ, full sample)
Grid pass_fraction 0.0 (no cell clears both Sharpe>=1.0 and MDD<=0.25
simultaneously in `grid_test.py`'s own pass criteria). Full-sample
validators confirm: weak Sharpe, TC-survival fails on sparse trade count
(16 over 7.5yr), and parameter sensitivity is highly unstable (rel_std
1.43, Sharpe swings from -1.08 to +0.87 across the small grid) — the raw
9-count Setup signal alone (without the Countdown confirmation phase) does
not have a robust edge on daily QQQ/SPY bars.
