# Backtest Report: Ehlers Ultimate Channel / Ultimate Bands trend-following

**Strategy file:** `strategies/2026-09-16_ultimate_channel_trend_following.py`
**Date:** 2026-09-16
**Source:** https://traders.com/Documentation/FEEDbk_docs/2024/05/TradersTips.html
(TASC May 2024 Traders' Tips, "Ultimate Channels And Ultimate Bands" by
John F. Ehlers)

## Hypothesis
Ultimate Channel (Keltner-style, centerline + band-width both built from
Ehlers' UltimateSmoother instead of SMA/EMA and raw ATR) and Ultimate Bands
(Bollinger-style, same UltimateSmoother centerline with a std-dev band).
Per the Wealth-Lab Traders' Tips implementer's direct quote of Ehlers' own
disclosed trading rule: "hold a position in the direction of the
UltimateSmoother and exit that position when the price pops outside the
channel or band in the opposite direction." Implemented long-only: long
while close > centerline, exit when close closes below the lower
channel/band. First Ultimate Channel/Ultimate Bands strategy in this repo.

## Step 6 — Grid test summary
Grid: `param_grid={length:[10,20,40], num_strs:[0.5,1.0,1.5], use_bands:[False,True]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
-> total_cells=216, passed=53, **pass_fraction=0.245**.
- by_asset_class: equity 48/108 (0.444), crypto 5/108 (0.046)
- by_vol_regime: low 41/72 (0.569), mid 9/72 (0.125), high 3/72 (0.042)

## Full-sample check (grid-best config per symbol)

| Symbol | Full-sample Sharpe | Full-sample MDD |
|---|---|---|
| QQQ | 1.038 (marginal pass) | 0.350 (**decisive fail**, >>0.25) |
| SPY | 0.893 (fail, <1.0) | 0.379 (**decisive fail**) |
| BTC/USDT | 0.997 (fail, just under 1.0) | 0.579 (**decisive fail**) |
| ETH/USDT | 1.043 (marginal pass) | 0.632 (**decisive fail**) |

All 4 symbols decisively fail max-drawdown at full exposure (roughly
1.4x-2.5x the 0.25 threshold) even where Sharpe marginally clears 1.0 --
the strategy is essentially "always in the market during any uptrend
regime" with no risk-control overlay, and Ehlers' own disclosed exit rule
(price pops below the lower band) triggers too rarely/too late to control
drawdown on daily bars. No full Step 7 validator suite run given this
decisive MDD failure across every symbol.

## Decision
**Reject** (all symbols, decisive on MDD). This differs from several other
this-cron-trigger pure-trend-following rejections (HalfTrend, CTI, TPR,
Coral Trend) that were later RESCUED with an inverse-volatility sizing
overlay -- but those all had Sharpe cleanly above 1.0 with only crypto
failing MDD; here BOTH equity and crypto fail MDD decisively and equity
Sharpe is itself only marginal, suggesting the exit rule (not just position
sizing) is the weaker link. Recorded as a lower-priority rescue candidate
than other near-misses this cron trigger -- if revisited, the fix would
need to combine both an earlier/tighter stop mechanism (the band-pop exit
alone is too loose) AND a position-sizing overlay, a two-part fix rather
than the single vol-targeting overlay that worked for the pure-trend-
following near-misses above.
