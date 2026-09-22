# Backtest report: PVO-Confirmed Donchian Breakout, ETH/USDT follow-up (REJECTED)

**Strategy file:** `strategies/2026-09-22_pvo_donchian_breakout.py` (same file as 2026-09-22-111, different symbol)
**Hypothesis id:** 2026-09-22-112
**Source:** same as 2026-09-22-111 (StockCharts ChartSchool PVO formula).

## Hypothesis

Direct follow-up for this same cron trigger's 2026-09-22-111 (rejected on QQQ), testing whether the same PVO-confirmed Donchian breakout mechanic holds up on ETH/USDT, whose grid cell (breakout_window=15/max_hold_days=15, mid-vol regime) showed the single best Sharpe (2.28) in the full grid.

## Full-sample validation across all 9 param combos (ETH/USDT, 2019-2026)

| breakout_window | max_hold_days | Sharpe | MDD |
|---|---|---|---|
| 15 | 15 | 1.24 (pass) | 0.338 (**fail**) |
| 15 | 20 | 1.12 (pass) | 0.362 (**fail**) |
| 15 | 30 | 1.00 (pass) | 0.426 (**fail**) |
| 20 | 15 | 1.22 (pass) | 0.330 (**fail**) |
| 20 | 20 | 1.19 (pass) | 0.334 (**fail**) |
| 20 | 30 | 1.03 (pass) | 0.418 (**fail**) |
| 30 | 15 | 1.09 (pass) | 0.384 (**fail**) |
| 30 | 20 | 1.00 (pass) | 0.486 (**fail**) |
| 30 | 30 | 0.85 (fail) | 0.527 (**fail**) |

Max drawdown fails the 0.25 threshold at EVERY tested parameter combination (range 0.33-0.53), despite Sharpe passing at 8/9 combos. This is a decisive, config-independent rejection -- the mid-vol-regime grid slice that looked attractive (Sharpe 2.28) evidently excludes a severe drawdown episode that dominates the full-sample picture, the same pattern already observed and documented in this cron trigger's iteration 7 (2026-09-22-109).

## Decision: REJECTED

Full-sample max drawdown fails decisively and consistently across the entire parameter grid on ETH/USDT. Combined with 2026-09-22-111's QQQ rejection, the PVO-confirmed-Donchian-breakout mechanic is rejected across both tested asset classes for this cron trigger. Strategy file and this report kept as a record.
