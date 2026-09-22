# Backtest Report: Monday Effect Avoidance (flat Mondays, long Tue-Fri)

**Strategy file:** `strategies/2026-09-22_monday_effect_avoidance.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-069

## Hypothesis

Per the Monday Effect / Weekend Effect literature (Cross 1973; Keef 2009
ScienceDirect; Linton 2006 FMG working paper; GRITTI 2024 "The Calendar
Effects in Financial Markets" thesis; Investopedia, all cited on the
Google SERP for the search query, read via browser_exec since
`web_search`'s DDGS backend intermittently TLS-errors), Monday stock
returns are, on average, statistically lower than -- and often negative
versus -- returns on other weekdays, a long-documented anomaly since
Cross's 1973 paper. Implemented as the simplest directly testable variant:
flat specifically on Mondays, long Tuesday-Friday. First
Monday-Effect/day-of-week strategy in this repo (0 prior KB hits).

## Grid Test Summary (Step 6)

- Total cells: 24 (2 avoid_weekdays configs [(Mon,), (Mon,Fri)], 3 vol
  regimes, QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.208 (5/24)
- By asset class: equity 5/12, crypto 0/12
- By vol regime: low 4/8, mid 1/8, high 0/8
- Best cell: QQQ, avoid_weekdays=(Mon,), low-vol regime, Sharpe 3.04
- Worst cell: SPY, avoid_weekdays=(Mon,Fri), mid-vol regime, Sharpe -0.01

## Single-Config Validation (Step 7), avoid_weekdays=(Monday,)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **false** 0.893 | **false** 0.763 | 1.0 |
| Max drawdown | **false** 0.374 | **false** 0.374 | 0.25 |
| Transaction cost survival (10bps/trade, 361 trades) | true net Sharpe 0.544 | **false** net Sharpe 0.357 | 0.5 |
| Walk-forward (manual 4-equal-slice) | true 0.75 | true 1.0 | 0.75 |
| Parameter sensitivity (2-value sweep) | true 0.147 | true 0.124 | 0.5 |

## Outcome: REJECTED (both symbols)

Decisive rejection on the two most consequential metrics: Sharpe ratio and
max drawdown both fail on both symbols. Because this strategy is long ~4
of every 5 trading days (only flat on Mondays), it is essentially "buy and
hold minus Mondays" -- MDD (37.4% on both symbols) is nearly identical to
what an unfiltered buy-and-hold would show over this sample (2020 COVID
crash, 2022 bear market), since skipping only 1 day/week doesn't
materially change the strategy's exposure to a sustained multi-week
drawdown. The very high trade count (361, i.e. essentially every week)
also means transaction costs meaningfully erode the modest edge from
avoiding Monday's statistically-weaker average return -- SPY's net Sharpe
after 10bps/trade costs actually fails outright (0.357 < 0.5). This
confirms the literature's own framing: the Monday effect is a small,
average-case return anomaly, not a mechanism for meaningfully reducing
drawdown risk or generating high risk-adjusted absolute returns on its
own. A future iteration could test avoiding Monday's return ONLY within an
already-selective trend-following or momentum entry (rather than as the
sole standalone signal), where the modest edge might tip an
already-marginal strategy over the line rather than needing to carry the
whole Sharpe/MDD burden itself.
