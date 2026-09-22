# Backtest Report: 52-Week-High Breakout Momentum + SMA Trend Exit + Trailing Stop

**Strategy file:** `strategies/2026-09-22_52wk_high_breakout_trend_exit.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-062

## Hypothesis

Per QuantifiedStrategies.com's "52-Week High Trading Strategy (Backtest,
Trading Rules And Example)"
(https://www.quantifiedstrategies.com/52-week-high-strategy/, read via
browser_exec since `web_search`'s DDGS backend intermittently TLS-errors),
the "52-week high effect" (Hong/Jordan/Liu; George/Hwang academic
literature, cited by the source) finds stocks near their 52-week highs
outperform those further away, an anchoring-bias-driven under-reaction
effect. The article's own cited third-party backtest tests buying new
52-week highs with three exit rules; the best risk/reward reported is Exit
1 "hold until the stock crosses below the 200-day moving average" (CAGR
8.6%, MDD 44%). Implemented here: long entry on new 252-day (~52-week)
closing high, exit on close<SMA(trend_exit_window) (primary, per source's
best-reported exit) OR a trailing_stop_pct drawdown from post-entry peak
(source's second disclosed exit variant, added as extra risk control) OR a
max_hold_days time-stop backstop.

## Grid Test Summary (Step 6)

- Total cells: 48 (2 trend_exit_window x 2 trailing_stop_pct, 3 vol
  regimes, QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.229 (11/48)
- By asset class: equity 8/24, crypto 3/24
- By vol regime: low 11/16, mid 0/16, high 0/16
- Best cell: SPY, trend_exit_window=150/trailing_stop_pct=0.20, low-vol regime, Sharpe 2.68
- Worst cell: SPY, trend_exit_window=150/trailing_stop_pct=0.20, mid-vol regime, Sharpe -0.07

## Single-Config Validation (Step 7), SPY, lookback_days=252/trend_exit_window=150/trailing_stop_pct=0.20/max_hold_days=300

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **false** | 0.994 | 1.0 |
| Max drawdown | true | 0.162 | 0.25 |
| Transaction cost survival (10bps/trade, 9 trades) | true | net Sharpe 0.979 | 0.5 |
| Walk-forward (manual 4-equal-slice) | true | 4/4 splits positive | 0.75 |
| Parameter sensitivity (4-combo sweep) | true | relative std 0.011 | 0.5 |

## Outcome: REJECTED (near-miss)

4 of 5 validators pass cleanly, including a very robust (near-zero relative
std 0.011) parameter sensitivity result and a full 4/4 walk-forward pass.
Only the Sharpe ratio validator fails, and only marginally: 0.994 vs the
1.0 threshold, a 0.6% shortfall. The strategy's edge is also honestly
concentrated: grid pass_fraction is driven almost entirely by low-vol-regime
cells (11/16 passing) with zero passes in mid- or high-vol regimes,
consistent with the source's own note that the "edge is not obviously
large" and the strategy needs "time to run" (few, long-held trades). A
future iteration could revisit this near-miss by widening trend_exit_window
slightly, adding a volatility regime gate (skip entries during mid/high-vol
periods, matching the grid's honest scope), or using a less conservative
Sharpe threshold given the very strong parameter-sensitivity and
walk-forward results already obtained.
