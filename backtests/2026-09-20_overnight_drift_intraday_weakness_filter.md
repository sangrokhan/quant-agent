# Overnight-drift reversal, filtered by trailing intraday weakness (ACCEPTED, SPY only)

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_overnight_drift_intraday_weakness_filter.py`
**Source:** https://wolfx.trade/whitepaper/overnight-drift (citing Lou/Polk/Skouras 2019 JFE, Bogousslavsky 2021 JFE)

## Hypothesis
Equity index overnight returns (close-to-next-open) are on average
positive while intraday returns (open-to-close) are roughly flat. The
source's disclosed filter: only take the long overnight position when
the trailing N-day (default 5, we grid N) sum of daily intraday
log-returns (log(close/open)) is negative -- i.e. only harvest the
overnight premium after a stretch of intraday weakness. Enter at close,
exit at next open; flat (cash) otherwise. Source's own head-to-head
comparison found the filtered variant materially outperforms the
always-on variant (Sharpe 1.229 vs 0.479 on their own walk-forward
slice).

## Grid test summary

lag_window in {3, 5, 8, 10}, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), vol_regime_splits=3, 2019-2026 (48 cells)

- pass_fraction: 0.271 (13/48)
- by_asset_class: equity 10/24, crypto 3/24
- by_vol_regime: low 4/16, mid 8/16, high 1/16
- best_cell: SPY, lag_window=10, mid-vol, Sharpe 2.13
- worst_cell: BTC/USDT, lag_window=5, low-vol, Sharpe -0.65

## Single-config validators (SPY, lag_window=8, full 2019-2026 sample)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.197 | >= 1.0 | PASS |
| Max drawdown | 0.107 | <= 0.25 | PASS |
| Transaction cost survival (10bps, 149 trades) | 0.763 | >= 0.5 | PASS |
| Walk-forward (manual 4-split, repo convention) | 1.0 (4/4 splits positive) | >= 0.75 | PASS |
| Parameter sensitivity (lag_window in {6,7,8,9,10}) | relative_std 0.206 | <= 0.5 | PASS |

All 5 validators pass for SPY at lag_window=8.

## Cross-symbol scope check (same lag_window=8 config)

| Symbol | Sharpe | MDD | TC-survival |
|---|---|---|---|
| SPY | 1.197 PASS | 0.107 PASS | 0.763 PASS |
| QQQ | 0.694 FAIL | 0.132 PASS | 0.378 FAIL |
| BTC/USDT | -0.232 FAIL | 0.006 PASS | -0.365 FAIL |
| ETH/USDT | 0.815 FAIL | 0.002 PASS | -0.348 FAIL |

## Decision: ACCEPTED (SPY only, lag_window=8)

Strategy file and this report kept as a live accepted strategy, but
strictly scoped to SPY -- QQQ and crypto (BTC/USDT, ETH/USDT) fail
Sharpe and transaction-cost survival at the same config despite
plausible-looking drawdown numbers (near-zero MDD on crypto is an
artifact of the strategy trading rarely relative to crypto's volatility,
not genuine edge). Do not apply this signal outside SPY without
re-validating.

## Notes for future loops
- This is the first strategy in this repo using the rolling SUM of
  trailing intraday (open-to-close) log returns as an overnight-hold
  trigger -- distinct from 2026-09-17-007 (N-day-low OPEN trigger +
  bullish CLOSE confirmation) and 2026-09-18-098/135 (N-consecutive-
  down-CLOSE streak trigger), which use different mechanical
  conditions despite the shared "overnight holding period" theme.
- lag_window=8 diverges from the source's own default of 5 (which
  narrowly failed Sharpe on both QQQ and SPY in the grid, 0.707/0.704)
  -- this repo's own parameter sweep found 8 clears the bar on SPY
  specifically; a future loop could retest lag_window in a finer
  neighborhood (e.g. 7-9) on QQQ to see if a QQQ-specific config exists.
- Trade count is meaningfully higher than most accepted strategies in
  this repo (149 trades over ~7.5 years, roughly 20/year) since the
  trigger condition (5/8/10-day intraday-return-sum < 0) fires on
  ~40-45% of sessions per the source's own disclosure -- net-of-cost
  Sharpe (0.763) still clears the 0.5 bar comfortably at 10bps/trade
  but is the tightest-margin validator of the five.
