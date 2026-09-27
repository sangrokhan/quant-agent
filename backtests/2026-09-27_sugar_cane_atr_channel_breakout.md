# Sugar (CANE) 350-day SMA + 7-day ATR Channel Breakout — rejected

**Hypothesis:** per
https://www.quantifiedstrategies.com/sugar-trading-strategy/ (Oddmund
Groette), a Turtle-style channel breakout — buy when price breaks above
SMA(350) + 7-day-ATR, sell/exit when price breaks below SMA(350) -
7-day-ATR — was the only variant the source found to show promise on raw
sugar futures. Adapted to CANE (Teucrium Sugar Fund ETF, continuously-rolled
sugar futures proxy) since this repo's data/loaders.py has no raw futures
data source. First Sugar/CANE strategy in this repo (0 prior KB hits).

**Strategy file:** `strategies/2026-09-27_sugar_cane_atr_channel_breakout.py`

## Grid test (Step 6)

`param_grid={sma_window:[200,350,500], atr_mult:[0.5,1.0,1.5]}`, symbols
equity=[CANE] crypto=[BTC/USDT,ETH/USDT] (crypto included as a structural
falsification check per this repo's convention, not because the hypothesis
is crypto-specific), vol_regime_splits=3, 2015-2026.

- pass_fraction 0.198 (16/81); equity 8/27, crypto 8/54; by_vol_regime low
  13/27, mid 3/27, high 0/27.
- Best cell Sharpe 1.78 (ETH/USDT, sma_window=200/atr_mult=0.5, mid-vol
  tercile) -- crypto, not the intended sugar/CANE hypothesis.

## Full-sample check on CANE

A 90-combo local search (`sma_window in [150..400] x atr_mult in
[0.3,0.5,0.75,1.0,1.5] x atr_window in [5,7,14]`) found a ceiling of
**Sharpe 0.854** (sma_window=400, atr_mult=1.0, atr_window=5, MDD 12.6%) --
but only **7 trades** over the full 2015-2026 sample, consistent with the
source's own observation that sugar trend-following captures "a few large
winning moves" (very sparse signal). Below this repo's 1.0 Sharpe threshold
and too few trades to be statistically reliable regardless.

## Outcome

**Rejected** — CANE (the sugar proxy the hypothesis is actually about) never
clears Sharpe 1.0 in either the grid or a 90-combo full-sample local search;
best full-sample config manages only 0.854 Sharpe on just 7 trades over 11+
years, an unreliably small sample. The grid's nominal "passing" cells are
concentrated in crypto (BTC/ETH), which is not what this hypothesis is
about and doesn't validate the sugar-specific claim.
