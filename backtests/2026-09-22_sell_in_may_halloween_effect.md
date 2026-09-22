# Backtest Report: Sell-in-May / Halloween Effect Seasonal (Nov-Apr Long, Flat May-Oct)

**Strategy file:** `strategies/2026-09-22_sell_in_may_halloween_effect.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-067

## Hypothesis

Per the "Sell in May and Go Away" / Halloween Effect literature (Bouman &
Jacobsen 2002, corroborated by Guo et al. 2014 and a 2018 65-market study,
all cited on the Google SERP for the search query, read via browser_exec
since `web_search`'s DDGS backend intermittently TLS-errors), average
6-month returns are ~4% higher November-April than May-October, a
long-studied global calendar anomaly. Disclosed rule (Investopedia,
Moomoo, CFI, all consistent): long Nov 1 - Apr 30, flat May 1 - Oct 31.
First Sell-in-May/Halloween-effect strategy in this repo (0 prior KB
hits).

## Grid Test Summary (Step 6)

- Total cells: 48 (2 long_start_month[10,11] x 2 long_end_month[4,5], 3
  vol regimes, QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.229 (11/48)
- By asset class: equity 9/24, crypto 2/24
- By vol regime: low 10/16, mid 1/16, high 0/16
- Best cell: SPY, long_start_month=10/long_end_month=5 (wider window), low-vol regime, Sharpe 1.88
- Worst cell: SPY, long_start_month=11/long_end_month=4 (source's exact rule), mid-vol regime, Sharpe -0.14

## Single-Config Validation (Step 7), long_start_month=11/long_end_month=4 (source's exact disclosed rule)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **false** 0.675 | **false** 0.580 | 1.0 |
| Max drawdown | **false** 0.286 | **false** 0.341 | 0.25 |
| Transaction cost survival (10bps/trade, 7 trades) | true net Sharpe 0.669 | true net Sharpe 0.573 | 0.5 |
| Walk-forward (manual 4-equal-slice) | true 0.75 | true 1.0 | 0.75 |
| Parameter sensitivity (4-combo sweep) | true 0.129 | true 0.135 | 0.5 |

## Outcome: REJECTED (both equity symbols)

3 of 5 validators pass on both symbols, but the two most consequential
metrics -- Sharpe ratio and max drawdown -- fail on both. Only 7 trades
(entry/exit cycles) fired over the full 2019-2026 sample, since the
strategy is invested for a fixed ~6-month calendar window every year
regardless of market conditions (unlike the turn-of-month strategies
tested this same cron trigger, this has no trend filter or selectivity at
all). This means the strategy is simply long the underlying for half the
calendar year with no risk management -- it inherits roughly half of any
major equity drawdown (COVID 2020, 2022 bear market) that happens to fall
in its Nov-Apr window, which is exactly what drove MDD above the 0.25
threshold (28.6% QQQ, 34.1% SPY). The academic literature's own framing is
about a modest RELATIVE outperformance of Nov-Apr vs. May-Oct on average,
not an absolute low-risk edge -- this repo's fixed Sharpe/MDD thresholds
are a much higher bar than "beats the other half of the year on average."
A future iteration could revisit this by adding a trend/volatility filter
within the Nov-Apr window (skip or reduce exposure during a confirmed
downtrend), similar to the turn-of-month rescue (2026-09-22-066) tested
earlier this same cron trigger.
