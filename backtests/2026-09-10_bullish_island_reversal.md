# Bullish Island Reversal (gap-down/range/gap-up), long-only

**Hypothesis source:** https://www.investopedia.com/terms/i/islandreversal.asp
Island reversal requires two price gaps in opposite directions isolating a
cluster of trading days. Implemented bullish variant: downtrend -> gap-down
day (today's high < yesterday's low) -> island cluster (up to
`max_island_days`) trading below that day's low -> gap-up day (today's low
clears both the island's own high and the original gap-down day's high) ->
long entry on the confirming gap-up day.

## Grid test (Step 6)

Attempted `param_grid={"trend_window":[30,50], "max_island_days":[3,5,7]}`
on `symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`.

**Result: 0 trades generated in every single grid cell (0/... cells with
any signal at all), across both asset classes and all parameter values.**
The strict two-gap isolation criterion (today's high strictly below
yesterday's low, AND a later day's low strictly clearing both the island's
own high and the original gap-down day's high) essentially never triggers
on daily OHLCV bars for these liquid, heavily-arbitraged
instruments (QQQ/SPY rarely gap by more than a few bps intraday-to-close on
a "close < next day's true range" basis; BTC/USDT and ETH/USDT trade
continuously 24/7 across many venues with negligible daily "overnight" gap
risk in this repo's data/loaders.py OHLCV feed).

## Decision

**Reject — feasibility/signal-sparsity dead end**, not a Sharpe/MDD
failure. No validators were run since there is no trade activity to
evaluate (all validators would be trivially undefined). This candidate
would need either (a) intraday/higher-frequency data where genuine price
gaps are more common, or (b) a much looser "gap" definition (e.g. percent
close-to-close jump rather than strict high/low non-overlap) to ever fire
on this repo's daily-bar QQQ/SPY/BTC/ETH data — logging as a feasibility
dead end rather than forcing a degenerate test.
