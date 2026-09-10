# 2026-09-10 Weinstein Stage 2 Breakout — Backtest Report

**Hypothesis (id 2026-09-10-127):** Stan Weinstein's Stage Analysis Stage-2
breakout — long entry on a close breaking above the rolling 50-day high
while price is above a RISING 150-day SMA (30-week MA proxy on daily bars);
exit on close < SMA, SMA turning flat/falling, or a 60-day time-stop.

**Source:** https://deepvue.com/indicators/stan-weinstein-stage-analysis/
(visited this iteration; corroborated by Google AI-overview SERP synthesis
of TraderLion/Equity Reads/TradingView/AXLFI — the latter two source pages
404'd when visited directly).

## Grid test summary (Step 6)

- Grid: `sma_window in [100,150,200] x breakout_window in [30,50,70] x
  sma_slope_lookback in [10,20]`, symbols `{equity: [QQQ, SPY], crypto:
  [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3. 216 total cells.
- `pass_fraction`: 43/216 = 0.199
- `by_asset_class`: equity 43/108 (0.398), crypto 0/108 (0.000 — decisive
  crypto rejection)
- `by_vol_regime`: low 36/72 (0.50), mid 7/72 (0.097), high 0/72 (0.000) —
  the edge, where it exists, is concentrated almost entirely in low-vol
  conditions.
- `best_cell`: sma_window=100/breakout_window=50/sma_slope_lookback=20,
  SPY, low-vol regime, Sharpe 2.81.

## Single-config validation (Step 7) — best grid config, full sample

Config: `sma_window=100, breakout_window=50, sma_slope_lookback=20,
max_hold_days=60`.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** 0.679 | **FAIL** 0.700 |
| Max Drawdown (<=0.25) | pass 0.142 | pass 0.098 |
| TC survival (net Sharpe >=0.5) | pass 0.653 | pass 0.658 |
| Walk-forward (>=0.75 splits positive) | pass 0.75 (3/4) | pass 0.75 (3/4) |
| Param sensitivity (rel std <=0.5) | pass 0.196 | pass 0.155 |

## Decision: REJECTED

Full-sample Sharpe fails on both QQQ (0.679) and SPY (0.700) — a moderate,
not razor-thin, miss (~0.3-0.32 below threshold), despite every other
validator (MDD, TC survival, walk-forward, param sensitivity) passing
cleanly. The grid's own `by_vol_regime` breakdown explains why: the strong
best-cell Sharpe (2.81) only shows up in the low-vol tercile; full-sample
performance is diluted by mid/high-vol periods where the single-SMA-slope
regime gate does not filter out enough chop. A future iteration could
revisit this with an explicit volatility-regime gate (same construction as
the accepted `2026-09-03_bb_meanrev_qqq_volregime.py`) restricting entries
to the low-vol tercile specifically, which the grid suggests could push
Sharpe well above 1.0.

Crypto is decisively rejected (0/108 grid cells) — Stage Analysis's
30-week-MA regime concept, built for slower-moving equity cycles, does not
translate to crypto's shorter/faster cycle structure.
