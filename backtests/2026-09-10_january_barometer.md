# Backtest Report: January Barometer (Yale Hirsch, 1972)

**Strategy file:** `strategies/2026-09-10_january_barometer.py`
**Hypothesis / source:** Yale Hirsch's January Barometer, 1972 (Stock
Trader's Almanac), corroborated by andersoneminitrading.com's disclosed
stat ("Since 1945, the S&P has risen in price during the month of January
63% of the time. When price rose [in January], the rest of the year also
tended to rise"). Rule: if January's own return is positive, hold long
February-December; if negative, stay flat the rest of the year. See
knowledge_base entry `2026-09-10-019` for full hypothesis text and
novelty rationale vs. this repo's other calendar-seasonality entries.

## No grid test (Step 6 note)

This strategy has NO tunable parameters (the rule is a fixed
January-return-sign check) -- there is nothing to grid-sweep across
parameter values. Per Step 6's own guidance this is scoped down to
symbol x vol-regime only where meaningful; given the very low trade
count (5-9 trades over the full sample, one decision per year), a
vol-regime split would leave most cells with 0-1 trades and is not
informative. Evaluated directly via Step 7's single-config validators
across all 4 target symbols instead.

## Single-config validation (Step 7)

| Symbol | Trades | Sharpe | MDD | TC survival | Walk-forward |
|---|---|---|---|---|---|
| SPY | 5 | PASS 1.121 | PASS 0.201 | PASS (net Sharpe 1.117) | PASS 4/4 (1.0) |
| QQQ | 7 | PASS 1.349 | **FAIL 0.286** | PASS (net Sharpe 1.346) | PASS 4/4 (1.0) |
| BTC/USDT | 5 | FAIL 0.929 | (not checked, Sharpe already fails) | -- | -- |
| ETH/USDT | 5 | FAIL 0.516 | (not checked, Sharpe already fails) | -- | -- |

Parameter sensitivity is not applicable (no tunable parameters exist).

## Decision

**Accepted for SPY only.** QQQ fails max_drawdown (0.286 > 0.25 threshold)
-- QQQ's higher volatility means a "long the rest of the year" regime bet
that goes wrong (e.g. 2022) draws down further than SPY's lower-beta
profile tolerates under this repo's fixed 25% MDD threshold. Both crypto
assets fail the Sharpe threshold outright (BTC 0.929 near-miss, ETH 0.516
clear miss) -- the January Barometer's seasonal/calendar-flow rationale
(tied to US fiscal-year fund-flow patterns) does not transfer to a 24/7
market with no January-specific institutional flow pattern.

## Scope note

Accepted for **SPY only**. Not accepted for QQQ (MDD fail) or crypto
(Sharpe fail both). A future loop should not assume this strategy
generalizes beyond SPY.
