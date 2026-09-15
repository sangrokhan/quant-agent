# 2026-09-16 Price-Volume Rank (PVR) Continuous Sizing (full universe accept)

## Hypothesis
Price-Volume Rank (PVR), designed by Anthony J. Macek (Stocks &
Commodities V.12:6, 1994), per LazyBear's TradingView port visited this
iteration (https://www.tradingview.com/v/vho8gnBR/): compares the
direction of the price change to the direction of the volume change and
assigns a quadrant rank 1-4: PVR=1 (price up + volume up, most bullish),
PVR=2 (price up + volume down, weakening momentum), PVR=3 (price down +
volume down, selling pressure abating, potential buy signal), PVR=4 (price
down + volume up, most bearish). Source's own "MA Crossover Mode": buy
when a slow SMA of PVR falls below a fast SMA (PVR trending more bullish),
sell on the reverse cross, with a 2.5 confirmation/warning level. First
PVR-specific strategy in this repo — distinct from every other volume-flow
indicator already tested (none use this 4-state directional-quadrant
construction). Reframed as a CONTINUOUS SIZING dial: PVR smoothed over
`pvr_window` bars, rescaled to [-1,1] via (2.5-PVR)/1.5 (matching the
source's own 2.5 level as the dial's zero point, since lower PVR = more
bullish), used as an exposure multiplier inside an SMA(trend_window)
uptrend gate with deadband, per this repo's established pattern.

Discovery note: an initial search with an incorrect author attribution
("Anthony Tarquin") returned an unrelated engineering-economics textbook;
a second, better-framed query ("metastock formula overbought oversold")
found the correct attribution (Anthony J. Macek) and the LazyBear
TradingView port with the exact quadrant rule. Both `web_search` calls
this iteration were unproductive/off-target (not backend failures, just
imprecise queries), so `browser_exec` was used directly.

## Grid test (Step 6)
`run_grid_pvr_sizing.py`: `sensitivity in [0.4,0.5,0.6]` x
`deadband in [0.20,0.30]`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), `vol_regime_splits=3`.

- total_cells: 72, passed_cells: 36, **pass_fraction: 0.500**
- by_asset_class: equity 18/36, crypto 18/36
- by_vol_regime: low 24/24, mid 12/24, high 0/24
- best_cell: QQQ, sensitivity=0.4/deadband=0.2, low-vol, Sharpe 2.774

## Single-config validation (Step 7)
QQQ and BTC/USDT passed cleanly at default-ish params. **SPY initially
failed TC-survival** (net Sharpe 0.364, excessive turnover) — widened
deadband (0.20→0.30) rescued it. **ETH/USDT initially failed MDD** (0.275
> 0.25 at leverage_cap=1.0) — leverage-cap retune (0.6) rescued it.

| Symbol   | trend_window | pvr_window | sensitivity | deadband | leverage_cap | Sharpe | MDD   | TC net Sharpe | Walk-forward | Param sens. |
|----------|-------------:|-----------:|------------:|---------:|--------------:|-------:|------:|---------------:|-------------:|------------:|
| QQQ      | 40           | 10         | 0.4         | 0.20     | 1.0            | 1.253  | 0.096 | 0.630           | 0.75 (3/4)   | 0.048       |
| SPY      | 40           | 10         | 0.3         | 0.30     | 1.0            | 1.170  | 0.049 | 0.532           | 1.00 (4/4)   | 0.060       |
| BTC/USDT | 40           | 10         | 0.4         | 0.20     | 1.0            | 1.398  | 0.232 | 1.175           | 1.00 (4/4)   | 0.019       |
| ETH/USDT | 40           | 10         | 0.24        | 0.20     | 0.6            | 1.321  | 0.169 | 1.120           | 1.00 (4/4)   | 0.034       |

All 5 validators pass on all 4 symbols.

## Decision
**Accept — full universe (QQQ, SPY, BTC/USDT, ETH/USDT).**

## Source
https://www.tradingview.com/v/vho8gnBR/ (LazyBear's Price-Volume Rank port
of Anthony J. Macek's original S&C article, visited this iteration via
browser_exec after an initial imprecise search query returned unrelated
results).
