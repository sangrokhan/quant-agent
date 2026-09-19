# Backtest Report: Pre-Holiday Effect

**Strategy file:** `strategies/2026-09-20_pre_holiday_effect.py`
**Date:** 2026-09-20
**Outcome:** REJECTED (decisive)

## Hypothesis

Per Investing.com's "Using The Pre-Holiday Effect As An Effective Trading
Strategy" (https://www.investing.com/analysis/pre-holiday-effect-200169596,
read via browser_exec fallback -- web_search DDGS backend hit repeated
TLS/connection-reset errors this iteration), citing Lakonishok & Smidt's
Journal of Finance study: "On the trading day prior to holidays, stocks
advance with disproportionate frequency and show high mean returns
averaging nine to fourteen times the mean return for the remaining days
of the year... over one third of the total return accruing to the market
portfolio over the 1963-1982 period was earned on the eight trading days
which each year fall before holiday market closings."

Mechanical rule tested: long the close-to-next-trading-day-close return on
the last trading day before each detected U.S. market holiday (detected
purely from the OHLCV data's own calendar gaps, without an external
holiday-calendar dependency), flat all other days.

## Full-sample results (SPY, QQQ, 2010-01-01 to 2026-09-01)

| Symbol | Sharpe | Max Drawdown | Pre-holiday days flagged |
|---|---|---|---|
| SPY | 0.012 | 0.133 | 155 (~9.4/year) |
| QQQ | 0.340 | 0.137 | 155 (~9.4/year) |

Both symbols show a near-zero (SPY) or weak (QQQ) Sharpe -- a decisive
failure, far from the 1.0 threshold and far from what the cited academic
study's own historical magnitude (9-14x average daily return) would
suggest if the effect still held in this more recent 2010-2026 sample.

## Analysis

The academic study cited (Lakonishok & Smidt, sample period 1963-1982)
is over 40 years old. Calendar anomalies like the pre-holiday effect are
widely documented in the academic literature (e.g. Ariel 1990, and
subsequent studies) as having weakened or disappeared in more recent
decades -- plausibly explained by increased market efficiency, algorithmic
trading arbitraging away well-known calendar patterns, or simply publication
of the effect causing its own decay ("return predictability decay" once an
anomaly becomes widely known and tradeable). This repo's 2010-2026 test
window is consistent with that broader finding: the effect that was large
and robust in the 1963-1982 sample no longer produces a tradeable edge.

## Decision

**REJECTED (decisive).** Sharpe near zero on SPY (0.012), weak on QQQ
(0.340), both far below the 1.0 threshold. This is a clean confirmation
that a well-known, decades-old academic calendar anomaly has decayed and
is not currently exploitable -- not a near-miss worth further parameter
tuning (there are no real parameters to tune in this construction; the
holiday-detection logic itself is deterministic).
