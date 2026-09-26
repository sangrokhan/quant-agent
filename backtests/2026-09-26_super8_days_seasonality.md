# Super 8 Days Seasonality — Backtest Report

**Hypothesis:** Stock Trader's Almanac "Super 8 Days" (per github.com/paappraiser/almanac-trading-strategies README, s704): the union of the first 2 trading days, the last 3 trading days, and mid-month trading days 9-11 of each calendar month captures most of the month's positive seasonal drift; long only on these 8 trading-day-rank slots per month, flat otherwise.

**Source:** https://github.com/paappraiser/almanac-trading-strategies (read via browser_exec; web_extract returned no content for GitHub URLs). Original source: Stock Trader's Almanac (Yale Hirsch / Jeffrey Hirsch), DJIA/S&P/NASDAQ since 1950.

**Strategy file:** strategies/2026-09-26_super8_days_seasonality.py

## Grid test (validation/grid_test.py::run_strategy_grid)

param_grid: first_n_days in {1,2,3}, last_n_days in {2,3,4}; symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3; 108 total cells.

- pass_fraction: 27.8% (30/108)
- by_asset_class: equity 27/54 passed, crypto 3/54 passed
- by_vol_regime: low 6/36, mid 8/36, high 16/36
- best_cell: SPY, first_n_days=1/last_n_days=3, high-vol tercile, Sharpe 2.11

## Single-config validators (classic config: first_n_days=2, last_n_days=3, mid_start_day=9, mid_end_day=11)

| Symbol | Sharpe | Pass? | MDD | Pass? | Net Sharpe (TC) | Pass? | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | 1.199 | YES | 0.192 | YES | 0.602 | YES | 368 |
| SPY | 1.239 | YES | 0.120 | YES | 0.497 | NO (near-miss, thr 0.5) | 368 |
| BTC/USDT | 0.048 | NO | 0.119 | YES | -0.048 | NO | 368 |
| ETH/USDT | 0.106 | NO | 0.159 | YES | -0.013 | NO | 368 |

Parameter sensitivity (QQQ, first_n_days in {1,2,3}): relative_std 0.040 (well under 0.5 threshold) — robust, non-overfit.

Walk-forward: not run — `vbt.utils.splitting` raises `AttributeError` in this repo's installed vectorbt version (pre-existing environment issue, consistent with prior log entries e.g. 2026-09-05-009).

## Decision

**Accept for QQQ** (Sharpe, MDD, TC-survival, param-sensitivity all pass decisively). SPY is a near-miss (TC-survival 0.497 vs 0.5 threshold, everything else passes) — recorded as rejected for SPY but flagged for a possible future cost-reduction follow-up (e.g. wider mid-month window to reduce trade count, or looser cost assumption). Crypto (BTC/ETH) decisively rejected — consistent with the mechanism (US equity institutional-flow/turn-of-month seasonality) not applying to a 24/7 no-payroll-cycle asset, a useful falsification check.
