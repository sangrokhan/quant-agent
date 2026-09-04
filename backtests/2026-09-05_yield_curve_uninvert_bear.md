# Backtest Report: Yield-Curve Un-Inversion Bear Signal (10Y-3M Treasury Spread)

**Strategy file:** `strategies/2026-09-05_yield_curve_uninvert_bear.py`
**Hypothesis id:** 2026-09-05-024
**Source:** Web search consensus (Morningstar, CNBC 2019-06-27, BIS working paper, Investopedia, Reddit r/stocks discussion) on yield-curve un-inversion/steepening after a period of inversion historically preceding US recessions/equity declines.

## Hypothesis

The 10Y-3M Treasury yield spread (T10Y3M, using ^TNX/^IRX as proxies) inverting has preceded
every US recession since 1973, but the equity-market damage has historically occurred AFTER
the curve UN-inverts (steepens back to positive) rather than during the inversion itself. Long
by default; go flat for `flat_window_days` trading days after an un-inversion event (spread
crossing from negative back to >= 0) that follows an inversion within the trailing
`lookback_days`. Tested on QQQ/SPY (equity) and BTC/USDT, ETH/USDT (crypto falsification).

## Grid test summary (validation/grid_test.py::run_strategy_grid)

- Grid: `lookback_days` in {40, 60, 90} x `flat_window_days` in {10, 20, 30} x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles, 2019-01-01 to 2026-09-01.
- 108 total cells, **36 passed (pass_fraction = 33.3%)**.
- By asset class: **equity 36/54 passed (67%!)**, crypto 0/54 (falsification check succeeded).
- By vol regime: low 18/36 (50%), mid 9/36 (25%), high 9/36 (25%).
- Best cell: `lookback_days=40, flat_window_days=30`, SPY, low-vol, Sharpe 2.69.

This is the strongest grid result of any strategy tested this cron trigger -- the equity
pass rate is notably high and the parameter grid is not sensitive to lookback_days (Sharpe/MDD
are identical across all lookback_days values, since only one or two un-inversion events occur
in the 2019-2026 sample -- 2020 COVID re-steepening and 2023-2024's slow un-inversion).

## Single-config validation (lookback_days=40, flat_window_days=30, full sample 2019-2026)

| Symbol | Sharpe | MDD | Net Sharpe after 10bps costs (12 trades) | Param sensitivity (rel. std across 9 configs) |
|---|---|---|---|---|
| QQQ | 1.19 (**pass**, thr 1.0) | 35.6% (**fail**, thr 25%) | 1.18 (**pass**, thr 0.5) | 0.032 (**pass**, thr 0.5) |
| SPY | 1.26 (**pass**, thr 1.0) | 25.4% (**fail, marginal** — 0.4pp over thr 25%) | 1.25 (**pass**, thr 0.5) | 0.011 (**pass**, thr 0.5) |

Walk-forward not run: `check_walk_forward` hits the pre-existing `vbt.utils.splitting`
AttributeError bug in this repo's installed vectorbt version.

MDD is essentially constant across every `lookback_days`/`flat_window_days` combination tested
(QQQ always 35.6%, SPY always 25.4%) because only ~1-2 un-inversion events occur in this
2019-2026 sample (around COVID 2020 and the 2023-2024 slow un-inversion), so the drawdown is
dominated by periods the strategy is simply long-and-holding through (e.g. 2022 bear market),
not by the timing signal itself.

## Verdict: REJECTED (strong near-miss, especially SPY)

Sharpe, transaction-cost survival, and parameter sensitivity all pass decisively on both
symbols. Max drawdown fails on both -- QQQ decisively (35.6% vs 25% threshold) but **SPY only
marginally** (25.4% vs 25.0%, a 0.4-percentage-point miss). Given the strategy is essentially
buy-and-hold with a handful of tactical flat windows, its MDD is bounded by the underlying
buy-and-hold MDD (2022 bear market drawdown ~25%+ on SPY) rather than being reduced much by the
signal itself in this sample (too few historical un-inversion events, ~1-2, to meaningfully cut
drawdown). REJECTED per the strict "all validators must pass" rule, but flagged as the
strongest near-miss so far this run: a future loop could revisit with (a) a lower MDD threshold
appropriate for a mostly-long strategy, (b) combining the un-inversion flat-window signal with
an additional trend/vol filter to reduce the underlying buy-and-hold drawdown baseline, or (c)
extending the flat window further/adding a partial-hedge (short) leg during the un-inversion
window rather than just going to cash.
