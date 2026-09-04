# Backtest Report: Bitcoin Halving "500-Day Rule" (long-only calendar rotation)

**Strategy file:** `strategies/2026-09-04_btc_halving_500day_rule.py`
**Date:** 2026-09-04
**Source:** Google AI-overview + TradingView (Money_addixt)/Binance Square/CoinDesk
(retrieved via browser_exec after web_search DDGS/Yahoo TLS failure)

## Hypothesis

Go long BTC 500 days before each halving, hold through the halving and
post-halving bull run, exit 500 days after the halving (source's original
rule flips to short at that point; this repo tests the long-only variant
per SAFETY.md, replacing the short leg with flat).

## Full-sample metrics (BTC/USDT, ETH/USDT; pre=500, post=500)

| Symbol   | Sharpe | Pass | MDD   | Pass | Days exposed |
|----------|--------|------|-------|------|--------------|
| BTC/USDT | 1.324  | Yes  | 0.633 | No   | 1998/2801 (71%) |
| ETH/USDT | 1.164  | Yes  | 0.682 | No   | 1998/2801 (71%) |

## Parameter sensitivity (pre_days/post_days_flip sweep: 300/300, 400/400,
500/500, 300/500, 500/300)

- Sharpe: passes at most configs for BTC (1.01-1.44), inconsistent for ETH
  (0.91-1.16, fails at the shortest 300/300 window).
- **MDD fails at EVERY tested config for BOTH symbols** (range 60.0%-68.2%,
  vs 25-35% budget) -- the strategy is long ~71% of the time during a
  multi-year period that includes the entire 2022 crypto bear market and
  the 2020 COVID crash, both of which fall inside the wide halving windows.

## Decision: REJECTED

Sharpe alone looks attractive (often >1.0), but max drawdown fails
decisively and consistently across every parameterization tested -- this is
not a near-miss. A ~71%-of-time long exposure to BTC/ETH over a ~7.7-year
window that includes 2022's ~75% drawdown cannot avoid a large MDD without
an active risk-management overlay (the calendar rule alone provides none).
Sharpe ratio alone is an incomplete risk picture for a strategy with this
much sustained directional exposure; the hard drawdown budget is the
correct gate here and it is not close.

Future idea: combine the halving-window long bias with an active
vol-targeting or trend-following overlay (e.g. only stay long within the
window AND while price is above its 200d SMA) to actually manage the
drawdown risk that the pure calendar signal ignores -- similar in spirit to
2026-09-03-003's vol-targeting overlay on momentum, or 2026-09-03-004's
200d trend-gate.
