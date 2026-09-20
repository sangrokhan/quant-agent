# On Neck Tall-Candle Yearly-Low Bullish Reversal — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_on_neck_tall_yearly_low.py`
**Outcome:** REJECTED

## Hypothesis

Per Bulkowski's Encyclopedia of Candlestick Charts summary
(https://www.thepatternsite.com/OnNeck.html, freely available), the On
Neck pattern (tall black candle in a downtrend, followed by a white candle
closing at/near bar1's low) theoretically signals bearish continuation but
tests bearish only 56% of the time ("near random"); the source's own
disclosed BEST-performing combination across all candlestick types is an
UP breakout in a bear market (+8.32% avg 10-day move, rank 6/103), with
additional disclosed conditioning: best when bar1 is "tall" and the
pattern occurs within a third of the yearly low. This strategy
operationalized exactly that best-performing combination as a long entry.
0 prior On Neck entries in this repo.

## Grid test (Step 6)

`param_grid={"tall_mult": [1.0,1.2,1.5], "near_low_pct": [0.33,0.5]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.028** (2/72 cells) — decisively weak.
- **by_asset_class:** equity 0/36 passed; crypto 2/36 passed.
- **by_vol_regime:** low 2/24; mid 0/24; high 0/24.
- **best_cell:** `tall_mult=1.0, near_low_pct=0.5`, ETH/USDT, low-vol
  regime, Sharpe 1.21 (tercile cherry-pick).
- **worst_cell:** `tall_mult=1.5, near_low_pct=0.33`, QQQ, high-vol
  regime, Sharpe -1.04.

Best full-sample Sharpe per symbol (across all 6 param combos): QQQ 0.454,
SPY 0.251, BTC/USDT 0.015, ETH/USDT 0.003 — none close to the 1.0
threshold anywhere.

## Decision

**Rejected.** Even applying Bulkowski's own disclosed best-performing
conditioning factors (tall candle + near yearly low), the strategy shows
no usable full-sample edge on any symbol tested; equity fails entirely
(0/36 grid cells) and crypto's 2 passing cells are low-vol-tercile
artifacts not reflected in full-sample Sharpe. Bulkowski's statistics are
based on "perfect trade" idealized entries/exits across a large universe
of stocks and market regimes over decades — they do not appear to transfer
to this repo's small QQQ/SPY/BTC/ETH universe over 2019-2026 with a
mechanical time-stop exit.
