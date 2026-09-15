# Backtest report: Halloween Effect Seasonal (2026-09-16)

**Strategy file:** `strategies/2026-09-16_halloween_effect_seasonal.py`
**KB entry:** `2026-09-16-187` (rejected)

## Hypothesis

Per the well-documented "Halloween Effect" / "Sell in May and Go Away"
seasonal anomaly (Google search synthesis of Quantified Strategies,
Emerald academic literature, Seasonality360, Investopedia, IG.com),
equity returns Nov 1 - Apr 30 are historically stronger than May 1 - Oct
31. Long (fully invested) during the winter half, flat during the summer
half. Distinct from this repo's existing Turn-of-Month (day-of-month) and
day-of-week seasonality entries — this is a half-year calendar-window
rule.

First Halloween Effect strategy in this knowledge base.

**Source:** Google search results synthesis, read via `browser_exec`
Google SERP.

## Single-config validators (2010-2026, full sample, no grid needed — pure
calendar rule with no tunable risk parameter beyond the fixed window)

| symbol | sharpe | mdd |
|---|---|---|
| QQQ | 0.698 ❌ | 0.286 ❌ |
| SPY | 0.691 ❌ | 0.341 ❌ |
| BTC/USDT | 0.659 ❌ | 0.793 ❌ |
| ETH/USDT | 0.697 ❌ | 0.797 ❌ |

All 4 symbols fail both Sharpe and MDD decisively. The strategy is
essentially a 6-month buy-and-hold window with zero risk management
(no stop-loss, no vol-targeting) — during the winter half, price still
suffers full market drawdowns whenever a market correction happens to
fall in Nov-Apr, which is common enough (e.g. Feb 2020 COVID crash,
Dec 2018 selloff) that MDD isn't materially better than passive
buy-and-hold.

## Decision

**Rejected.** Decisive failure on all 4 symbols/both validators. The
seasonal edge (if any) documented in academic literature is typically a
small return-differential effect, not large enough to overcome the lack of
any drawdown control in a raw long/flat calendar implementation. Not worth
pursuing further parameter variations since there are no tunable
parameters beyond the calendar window itself (already tried the
literature-standard Nov-Apr framing).
