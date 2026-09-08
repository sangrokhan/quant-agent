# Backtest Report: Sell in May / Halloween Effect Calendar Seasonality

**Strategy file:** `strategies/2026-09-09_sell_in_may_halloween_effect.py`
**Date:** 2026-09-09
**Source:** Google AI-overview synthesis of QuantPedia/QuantifiedStrategies "Sell in May Halloween effect" pages

## Hypothesis

The "Halloween Indicator" (Bouman & Jacobsen 1997 and many replications,
synthesized via QuantPedia) documents that equity returns from
November-through-April have historically been materially higher than
returns from May-through-October. Mechanical rule: 100% long equities
Nov 1 - Apr 30, flat May 1 - Oct 31 (approximated as flat rather than
cash/bonds since this repo's loaders have no bond-yield proxy). First
broad 6-month/6-month calendar-seasonality strategy in this repo, distinct
from narrower sub-month calendar effects (Turn-of-Month, January effect,
Santa Claus rally) already tested.

## Grid test summary (Step 6)

Grid: `long_start_month` in [10, 11], `long_end_month` in [3, 4, 5] x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.181** (13/72 cells passed -- the best of this cron trigger's iterations)
- **By asset class:** equity 13/36 passed, **crypto 0/36 passed** (decisive; crypto has no seasonal calendar structure the source's rationale would predict)
- **By vol regime:** low 12/24, mid 1/24, high 0/24 (edge concentrated in calm markets)
- **Best cell:** SPY, long_start_month=10, long_end_month=3, low-vol regime, Sharpe=2.138
- **Worst cell:** SPY, long_start_month=11, long_end_month=3, mid-vol regime, Sharpe=-0.470

## Single-config validation (Step 7): long_start_month=10, long_end_month=3, full sample 2018-2026

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.414 (FAIL) | 0.334 (FAIL) | >= 1.0 |
| Max drawdown | 0.311 (FAIL) | 0.341 (FAIL) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.401 (FAIL) | 0.318 (FAIL) | >= 0.5 |
| Walk-forward pass fraction (4 slices) | 0.75 (PASS, marginal) | 0.75 (PASS, marginal) | >= 0.75 |
| Parameter sensitivity relative std | 0.274 (PASS) | 0.300 (PASS) | <= 0.5 |
| Num trades | 17 | 17 | -- |

## Decision

**Reject.** Full-sample Sharpe (0.414/0.334) and MDD (0.311/0.341, both
breaching the 25% threshold) fail decisively despite the grid's isolated
low-vol-tercile cell looking excellent (Sharpe 2.14). Being long
7 months/year captures full exposure to whatever drawdowns occur within
that window regardless of the source's own low-vol-tercile framing --
full-sample testing (which necessarily spans multiple vol regimes over
8.7 years including 2020 and 2022 drawdowns) shows the calendar effect
alone, without any additional trend/volatility filter, is not a
sufficient risk-adjusted edge on its own. The one genuinely promising
signal from this iteration -- pass_fraction 0.181 was this cron trigger's
best grid result -- suggests a future iteration could productively
revisit this exact calendar window ADDED AS A FILTER on top of an
existing trend-following or vol-regime-gated strategy already accepted
in this repo, rather than as a standalone always-invested seasonal rule.
