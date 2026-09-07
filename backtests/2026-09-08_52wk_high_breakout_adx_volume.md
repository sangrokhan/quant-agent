# 52-Week-High Breakout with Volume + ADX Confirmation

**Strategy file:** `strategies/2026-09-08_52wk_high_breakout_adx_volume.py`
**Source:** https://swingfolio.com/blog/52-week-high-breakout-trading-strategy

## Hypothesis

Close breaking above the highest close of the last 252 trading days
("52-week high") clears overhead resistance from trapped sellers, and new
highs tend to keep making new highs. Source's specific entry checklist:
close > 252-day rolling high AND volume >= 1.5x 50-day avg volume
(institutional confirmation) AND ADX(14) > 20 and rising (real-trend
confirmation, avoids sideways-drift fakeouts). Exit: close below 20-day
EMA (trend-break) OR 7% trailing stop from post-entry peak.

## Grid test summary (Step 6) — decisive rejection, no Step 7 validators run

`param_grid`: `vol_mult in {1.2,1.5}`, `adx_threshold in {15,20}`,
`trail_pct in {0.07,0.12}`; `vol_regime_splits=3`; symbols: equity
QQQ/SPY, crypto BTC/USDT/ETH/USDT.

| asset_class | pass_fraction | low-vol | mid-vol | high-vol |
|---|---|---|---|---|
| equity (QQQ/SPY) | 0/48 (0.0) | 0/32 | 0/32 | 0/32 |
| crypto (BTC/ETH) | 0/48 (0.0) | 0/32 | 0/32 | 0/32 |

Overall pass_fraction 0/96 — decisive rejection across every cell, every
asset class, every vol regime. Best cell (SPY low-vol, vol_mult=1.2,
adx_threshold=15, trail_pct=0.07) only reached Sharpe 0.834, still well
below the 1.0 threshold; every other cell was worse, several strongly
negative.

## Decision: **REJECTED** (decisive — did not proceed to Step 7 validators)

## Notes for future iterations

The triple-confirmation entry filter (breakout + volume + rising ADX) may
be too restrictive for this repo's small symbol universe (QQQ/SPY/BTC/ETH)
— the source's own framing assumes screening across a broad stock
universe to find individual tickers meeting all three conditions
simultaneously, which is a very different setup than testing the
condition repeatedly on the SAME index-tracking ETF/major-crypto-pair over
time. A future iteration could try relaxing to fewer confirmation filters
(e.g. breakout + volume only, dropping the ADX gate) or testing on
individual growth/momentum stocks rather than index ETFs if the loaders
are ever extended beyond QQQ/SPY/BTC/ETH. Not worth further grid-tuning
this exact 3-filter combination on the current symbol set.
