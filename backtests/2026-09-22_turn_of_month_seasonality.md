# Backtest Report: Turn-of-the-Month (Ultimo Effect) Calendar Seasonality

**Strategy file:** `strategies/2026-09-22_turn_of_month_seasonality.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-065

## Hypothesis

Per QuantifiedStrategies.com's "The Turn Of The Month Trading Strategy
(Ultimo Effect) - Backtest and Trading Rules"
(https://www.quantifiedstrategies.com/turn-of-the-month-trading-strategy/,
read via browser_exec since `web_search`'s DDGS backend intermittently
TLS-errors), the turn-of-the-month effect is a well-documented calendar
anomaly with likely structural drivers (payroll investing, fund
rebalancing flows). Source's disclosed rule: "go long at the close on the
fifth last trading day of the month, and exit after seven days, i.e. at
the close of the third trading day of the next month" (~33% market
exposure). Source reports S&P 500 since 1960: CAGR 7.11% (vs buy-hold
6.95%) with MDD 27% (vs buy-hold 56%). Implemented directly: purely
calendar-driven, no price-derived indicator, entering on the Nth-to-last
trading day of each month and holding for a fixed number of trading days.
First "turn of month" calendar-seasonality strategy in this repo (0 prior
KB hits).

## Grid Test Summary (Step 6)

- Total cells: 48 (2 entry_days_before_month_end[3,5] x 2 hold_days[5,7], 3
  vol regimes, QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.271 (13/48)
- By asset class: equity 10/24, crypto 3/24
- By vol regime: low 3/16, mid 2/16, high 8/16 (spread across regimes,
  unlike most other strategies in this repo -- consistent with a
  calendar-driven rather than trend/momentum-driven mechanism)
- Best cell: BTC/USDT, entry_days_before_month_end=5/hold_days=7, high-vol regime, Sharpe 1.56
- Worst cell: BTC/USDT, entry_days_before_month_end=3/hold_days=5, mid-vol regime, Sharpe -0.58

## Single-Config Validation (Step 7), entry_days_before_month_end=5/hold_days=7 (source's exact disclosed rule)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **false** 0.895 | **false** 0.883 | 1.0 |
| Max drawdown | true 0.182 | true 0.155 | 0.25 |
| Transaction cost survival (10bps/trade, 92 trades) | true net Sharpe 0.758 | true net Sharpe 0.703 | 0.5 |
| Walk-forward (manual 4-equal-slice) | true 4/4 | true 4/4 | 0.75 |
| Parameter sensitivity (4-combo sweep) | true 0.080 | true 0.185 | 0.5 |

## Outcome: REJECTED (near-miss, both equity symbols)

4 of 5 validators pass cleanly on both QQQ and SPY -- MDD comfortably
under threshold, strong TC-survival margin despite ~92 trades over the
sample, a perfect 4/4 walk-forward, and very robust (low relative std)
parameter sensitivity. Only the Sharpe ratio validator fails, and only
narrowly: 0.895 (QQQ) and 0.883 (SPY) vs. the 1.0 threshold, both within
~11-12% of passing. This closely tracks the source's own framing of a
modest-but-persistent, low-exposure calendar edge rather than a
high-Sharpe strategy -- the source's own reported ~7% CAGR is not far above
buy-and-hold, it is the reduced drawdown/exposure that is the real
selling point, which this repo's fixed 1.0 Sharpe threshold does not
directly credit. A future iteration could revisit this near-miss by
combining the calendar entry with a simple trend filter (e.g. skip entries
when the broader market is in a confirmed downtrend), or by testing
whether widening the entry window (e.g. entry_days_before_month_end
7 or 4, closer to variants some sources describe) improves risk-adjusted
return enough to clear the Sharpe bar.
