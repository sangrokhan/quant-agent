# Short the Last Trading Day of the Month (SPY)

**Date:** 2026-09-23
**Source:** https://www.quantifiedstrategies.com/last-trading-day-of-the-month/
**Strategy file:** `strategies/2026-09-23_last_trading_day_month_short.py`

## Hypothesis
Source's own SPY backtest (1993-2021) reports the open-to-close intraday
return on the LAST trading day of each month averages -0.11% (win rate
42%), decisively worse than an average day, while the overnight leg into
that day is roughly average. We test: short SPY/QQQ/BTC/ETH at the open of
the last trading day of the month, cover at that same day's close, flat
all other times.

## Grid test summary (allow_short=True only, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- **12 total cells, 4 passed (pass_fraction = 0.333)**
- By asset class: equity 2/6, crypto 2/6
- By vol regime: low 2/4, mid 2/4, high 0/4
- Best cell: BTC/USDT, mid-vol, Sharpe 1.47
- Worst cell: SPY, high-vol, Sharpe -1.16

## Single-config validators (SPY, allow_short=True, full sample 2018-2026)

| Validator | Value | Result |
|---|---|---|
| Sharpe ratio (>=1.0) | -0.114 | **FAIL** (decisively negative) |
| Max drawdown (<=25%) | 9.7% | pass |
| Transaction cost survival (net Sharpe >=0.5 @ 10bps) | -0.381 | **FAIL** |
| Walk-forward (4-split, >=75% positive-Sharpe splits) | 50% (2/4 splits positive) | **FAIL** |

Only 104 signal days over 8.5 years (one per month) -- on our own
2018-2026 SPY sample the mean intraday return on the signal day is actually
slightly negative for the SHORT position (i.e. the underlying long
open-to-close return on the last trading day was close to flat/slightly
positive in this more recent window), directly contradicting the source's
own older (1993-2021) finding. This looks like a case of a historical
seasonal effect that has decayed/reversed in the post-2018 sample -- a
common outcome for well-known calendar anomalies once they're published and
potentially arbitraged away.

## Decision: REJECTED

Decisive full-sample Sharpe failure (negative), transaction-cost survival
failure, and walk-forward failure (only 50% of quarters positive) on SPY,
the source's own primary asset. Not promoted further to QQQ/crypto given
the equity decisive reject on the intended target asset.
