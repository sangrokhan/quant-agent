# Backtest report: Market Profile Value Area 80% Rule Re-entry (2026-09-16)

**Strategy file:** `strategies/2026-09-16_market_profile_value_area_reentry.py`
**KB entry:** `2026-09-16-183` (rejected)

## Hypothesis

Per Market Profile/TPO's "80% Rule" (Google AI-overview synthesis of
FTMO/MetroTrade/ThinkMarkets), a price move outside the Value Area
(VAH/VAL, the band containing ~70% of volume) followed by 2 consecutive
periods holding back inside signals an ~80% probability rotation to the
opposite Value Area edge. The source's rule uses intraday 30-minute TPO
blocks; this repo's data is daily-bar-only, so adapted to a daily-bar
analogue: rolling `lookback_n`-day volume-weighted Value Area (POC-expand
algorithm), "2 consecutive TPO blocks" → 2 consecutive daily closes. Long
entry on 2nd consecutive close back inside VAL after a prior close below
it; target VAH, stop below the re-entry VAL.

First Market Profile/TPO/Value Area strategy in this knowledge base.

**Source:** Google AI-overview synthesis, read via `browser_exec` Google
SERP.

## Grid test (Step 6)

`GridSpec(param_grid={"lookback_n": [15,20,30], "value_area_pct":
[0.6,0.7,0.8]}, symbols={"equity": ["QQQ","SPY"], "crypto":
["BTC/USDT","ETH/USDT"]}, vol_regime_splits=3)` — 108 cells, 2018-01-01 to
2026-09-01.

| metric | value |
|---|---|
| pass_fraction | 13/108 = 0.120 |
| by_asset_class | equity 9/54, crypto 4/54 |
| by_vol_regime | **low 13/36, mid 0/36, high 0/36** |
| best cell | ETH/USDT, lookback_n=20/value_area_pct=0.7, low-vol, Sharpe 1.928 |
| worst cell | SPY, lookback_n=15/value_area_pct=0.7, mid-vol, Sharpe -1.215 |

All 13 passing cells are in the low-vol-regime tercile — zero passes in
mid or high vol. Full-sample default config (QQQ, lookback_n=20,
value_area_pct=0.7): Sharpe -0.203, MDD 0.380 — decisive fail.

## Decision

**Rejected.** Pass fraction is small (12%) and entirely concentrated in
the low-vol-regime slice; full-sample performance for any tested config is
negative-Sharpe/high-drawdown. The intraday-native "80% Rule" logic likely
loses its statistical edge when reduced to daily-bar granularity (the
source's own confirmation window of "2 consecutive 30-min TPO blocks"
becomes "2 consecutive trading days" — a much coarser, noisier
approximation of the original concept). Worth flagging for a future loop:
this strategy family may need genuinely intraday (hourly/30-min) OHLCV
data to work as intended — this repo's daily-bar-only equity loader is a
structural limitation for TPO/Market-Profile-style strategies (same
feasibility caveat previously noted for equity ORB, 2026-09-10-026).
