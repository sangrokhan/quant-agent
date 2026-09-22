# Backtest Report: RSI(2) Mean Reversion + Third-Calendar-Week-of-Month Exclusion Filter

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_rsi2_third_week_exclusion_filter.py`
**Source:** [StatOasis — "RSI Deep Dive: How to Trade the S&P 500 Like a Pro with Mean Reversion"](https://statoasis.com/overfit/research/rsi-deep-dive-how-to-trade-the-sp500-like-a-pro-with-mean-reversion) (Ali Casey)

## Hypothesis

Per StatOasis's 146,880-combination grid search of RSI(2) mean-reversion
parameters, the single most robust configuration was Entry RSI(2)<25, Exit
RSI(2)>65 or after 5 bars. The source separately reports that adding a
**third-calendar-week-of-month exclusion filter** (no new entries during
days 15-21 of the calendar month) reduces noise/risk exposure at only a
small net-profit cost. This is the first strategy in this repo to combine
the well-established RSI(2)+SMA(200) mean-reversion mechanic with a pure
calendar-week entry-suppression overlay (distinct from every prior RSI(2)
variant, which vary the oscillator construction, trend gate, or
exit-mechanic instead).

## Single-config metrics (best grid cell: entry_threshold=25, exit_bars=8, trend_sma=200)

| Symbol | Sharpe | Max DD | TC-survival (net Sharpe) | Walk-forward pass frac | Param sensitivity (rel std) |
|--------|--------|--------|---------------------------|--------------------------|------------------------------|
| QQQ    | 1.132 (PASS) | 0.088 (PASS) | 0.648 (PASS) | 1.00 (PASS) | 0.061 (PASS) |
| SPY    | ~0.82 avg-grid; single-config not separately Sharpe-tested here, but | 0.114 (PASS) | 0.255 (**FAIL**, threshold 0.5) | 0.75 (PASS, borderline) | 0.220 (PASS) |

Full validator JSON: `validate_result_rsi2_third_week_exclusion_QQQ.json`,
`validate_result_rsi2_third_week_exclusion_SPY.json`.

## Grid summary (`grid_summary_rsi2_third_week_exclusion.json`)

- Grid: `entry_threshold` in {20,25,30} x `exit_bars` in {5,8}, symbols
  {QQQ,SPY} (equity) + {BTC/USDT,ETH/USDT} (crypto), `vol_regime_splits=3`.
- Total cells: 72. Passed: 19 (pass_fraction 0.264).
- By asset class: equity 16/36 (44.4%), crypto 3/36 (8.3%).
- By vol regime: low 9/24, mid 6/24, high 4/24 (edge concentrated in
  lower-volatility regimes, consistent with mean-reversion strategies
  generally).
- Best cell: SPY, entry_threshold=30/exit_bars=5, low-vol regime, Sharpe
  1.605.
- QQQ average Sharpe across vol regimes at entry_threshold=25/exit_bars=8:
  1.133 (best average config for QQQ).

## Pass/fail per validator (QQQ, primary accepted config)

- Sharpe ratio: **PASS** (1.132 > 1.0)
- Max drawdown: **PASS** (0.088 < 0.25)
- Transaction cost survival: **PASS** (net Sharpe 0.648 > 0.5 at 10bps/trade, 211 trades)
- Walk-forward (4 splits): **PASS** (4/4 splits positive Sharpe, pass_fraction 1.0)
- Parameter sensitivity: **PASS** (relative std 0.061 across the 6-config grid neighborhood)

## Pass/fail per validator (SPY)

- Sharpe ratio: not independently re-run at this exact single config, but grid-cell average Sharpe (0.82-1.11 depending on exit_bars) suggests it would likely pass.
- Max drawdown: **PASS** (0.114 < 0.25)
- Transaction cost survival: **FAIL** (net Sharpe 0.255 < 0.5 threshold, 203 trades — turnover too high relative to edge)
- Walk-forward: **PASS** (borderline, 3/4 splits positive, pass_fraction exactly 0.75)
- Parameter sensitivity: **PASS** (relative std 0.220)

Crypto (BTC/USDT, ETH/USDT): decisively rejected (3/36 grid cells passed,
consistent with this repo's established finding that daily-bar RSI(2)
mean-reversion generally does not transfer to crypto).

## Decision

**Accept QQQ only** (entry_threshold=25, exit_bars=8, trend_sma=200,
exclude_week=3). All 5 validators pass cleanly. **Reject SPY** (TC-survival
decisive fail — the calendar-week exclusion filter does not reduce
turnover enough on SPY to survive realistic transaction costs at the same
parameters; a future iteration could retune exit_bars wider for SPY
specifically). **Reject crypto** (no options-expiration/calendar-week
mechanism expected to transfer, and grid confirms decisive failure).
