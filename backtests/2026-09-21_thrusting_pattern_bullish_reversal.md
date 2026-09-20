# Thrusting Pattern Bullish Reversal — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_thrusting_pattern_bullish_reversal.py`
**Outcome:** REJECTED

## Hypothesis

Per Thomas Bulkowski's Encyclopedia of Candlestick Charts summary
(https://www.thepatternsite.com/Thrusting.html, freely available), the
Thrusting Candlestick pattern (bar1 bearish in a downtrend, bar2 gaps below
bar1's low then closes near-but-below bar1's body midpoint) theoretically
signals bearish continuation but Bulkowski's own large-sample testing found
it acts as a bullish reversal 57% of the time (overall performance rank
15/103). This strategy tested that empirically-observed bullish-reversal
behavior directly. 0 prior Thrusting Pattern entries in this repo.

## Grid test (Step 6)

`param_grid={"near_pct": [0.5, 0.8, 1.0], "trend_lookback": [5, 10]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.056** (4/72 cells) — decisively weak.
- **by_asset_class:** equity 4/36 passed; crypto 0/36 passed.
- **by_vol_regime:** low 4/24; mid 0/24; high 0/24.
- **best_cell:** `near_pct=0.8, trend_lookback=5`, QQQ, low-vol regime,
  Sharpe 1.66 (tercile cherry-pick).
- **worst_cell:** `near_pct=1.0, trend_lookback=5`, QQQ, mid-vol regime,
  Sharpe -1.26.

Full-sample Sharpe by config (QQQ, own-data recalibration): near_pct=0.5
tl=5/-0.578 (only 2 entries -- too sparse), near_pct=0.8 tl=5/0.101,
near_pct=0.8 tl=10/-0.050, near_pct=1.0 tl=5/0.271, near_pct=1.0
tl=10/0.154. None come close to the 1.0 Sharpe threshold; the best grid
tercile cell (1.66) is entirely a low-vol-tercile artifact absent from the
full-sample number for the same config (0.101).

## Decision

**Rejected.** Full-sample Sharpe never exceeds 0.27 across the tested
parameter combinations (best case QQQ, near_pct=1.0, trend_lookback=5).
The pattern is either too sparse (near_pct=0.5, only 2 signals over 7.5yr)
or, once loosened enough to get a usable sample size, shows no real edge.
Consistent with Bulkowski's own "near random" characterization of the
Thrusting pattern's directional predictability -- the modest overall
performance rank in his encyclopedia appears not to translate into a
standalone tradeable signal on this repo's QQQ/SPY/crypto sample without
additional confirmation filters beyond trend/gap/midpoint alone.
