# Backtest Report: SLV Winter-Months Seasonality

**Strategy file:** `strategies/2026-09-20_slv_winter_seasonality.py`
**Date:** 2026-09-20
**Outcome:** REJECTED (decisive)

## Hypothesis

Per QuantifiedStrategies.com's "Best Silver Trading Strategy | Rules,
Settings, And Backtest"
(https://www.linkedin.com/pulse/best-silver-trading-strategy-rules-settings-backtest-srrlf,
read via browser_exec fallback -- web_search DDGS backend hit repeated
TLS/connection-reset errors this iteration), the disclosed seasonality
claim: "Silver contracts, like gold, have been found to perform quite
well in the winter months. Performance during spring and fall is mixed.
It does poorly during the summer." (The article's own specific
day-trading strategy with concrete entry/exit rules is explicitly
withheld by the source and NOT implemented here -- only this disclosed
qualitative seasonality claim is tested.)

Mechanical rule: long SLV during winter months, flat otherwise. Tested
several winter-window definitions.

## Results (SLV, 2008-01-01 to 2026-09-01)

| Winter window | Sharpe | Max Drawdown |
|---|---|---|
| Dec-Feb (calendar winter) | 0.631 | 0.371 (fails) |
| Nov-Feb | 0.623 | 0.371 (fails) |
| Nov-Mar | 0.487 | 0.535 (fails badly) |
| Dec-Jan | 0.561 | 0.314 (fails) |

Every window tested decisively fails the max drawdown threshold (best
0.314 vs 0.25 required), even though Sharpe is a moderate near-miss at
the best config (0.631). SLV's high volatility (silver is a notoriously
volatile commodity, as the source's own article notes: "we believe
silver, together with most commodities, is very hard to trade") means
even a directionally-correct seasonal filter still carries large drawdown
risk from being fully long (unleveraged) through any winter that happens
to include a sharp correction (e.g. winter 2012-13 into the 2013 silver
crash).

## Decision

**REJECTED (decisive on MDD across all windows tested).** The qualitative
seasonality claim may have some directional truth (Sharpe 0.5-0.63 across
windows, all positive) but a raw long-only seasonal filter without any
risk management (position sizing, stop-loss, or a trend/volatility gate)
cannot survive SLV's drawdown profile. A future loop could revisit by
combining this seasonal window with a volatility-scaled position size or
a trend confirmation filter (e.g. only trade the winter window when SLV
is also above its own trend SMA) rather than a raw calendar-only signal.
