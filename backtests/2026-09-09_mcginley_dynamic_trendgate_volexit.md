# McGinley Dynamic Crossover with 200d SMA Trend Gate + Vol-Regime Exit — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_mcginley_dynamic_trendgate_volexit.py`
**Knowledge base id:** 2026-09-09-049

## Hypothesis

Direct follow-up to this repo's near-miss 2026-09-04-127 (unconditional
McGinley Dynamic fast/slow crossover, decisive high-vol-regime Sharpe fail,
0/24 high-vol grid cells). Adds (a) a 200-day SMA uptrend gate on entry
(per this repo's repeated finding that this filter improves crossover
setups, and per fxopen.com's own "higher-timeframe veto" suggestion,
visited this iteration) and (b) a realized-volatility regime EXIT (flatten
if 20d realized vol > 1.5x its trailing-year median), targeting -127's
specific failure mode directly rather than hoping the SMA filter alone
fixes it.

## Source URLs (visited this iteration)

- https://www.google.com/search?q=%22Relative+Strength%22+sector+rotation... (sector rotation -- saturated, not used)
- https://www.google.com/search?q=Know+Sure+Thing+KST... (KST -- saturated, not used)
- https://www.google.com/search?q=Hurst+exponent+trend+vs+mean+reversion... (Hurst -- already tested both directions, not used)
- https://www.google.com/search?q=McGinley+Dynamic+indicator+trading+strategy+rules+crossover (used -- confirmed standard crossover rule + higher-timeframe veto filter idea)

## Step 6 grid test summary

Grid: `fast_n` in {8,10,14} x `slow_n` in {30,40} x {QQQ, SPY, BTC/USDT,
ETH/USDT} x low/mid/high vol terciles, 72 cells, 2018-01-01 to 2024-12-31.

- **pass_fraction:** 0.208 (15/72)
- **by_asset_class:** equity 15/36, crypto 0/36 (decisive -- out of scope)
- **by_vol_regime:** low 7/24, mid 8/24, high 0/24 (STILL decisive fail --
  the vol-regime exit filter did not fix the high-vol collapse; it only
  reduces exposure during those regimes, doesn't eliminate losing trades
  that start just before a vol spike)
- **best_cell:** fast_n=8, slow_n=30, SPY, low-vol, Sharpe=2.363
- **worst_cell:** fast_n=8, slow_n=40, QQQ, high-vol, Sharpe=-1.084

## Step 7 single-config validation (primary config: fast_n=8, slow_n=30)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.923 | 1.555 | >= 1.0 | QQQ near-miss (0.077 short); SPY pass |
| Max drawdown | 0.045 | 0.024 | <= 0.25 | Yes (both) |
| Net Sharpe after costs (10bps/trade, 8 trades) | 0.879 | 1.475 | >= 0.5 | Yes (both) |

## Decision: **REJECTED (near-miss, improved over 2026-09-04-127 but not clearing threshold jointly)**

The two added filters meaningfully improved the strategy: QQQ Sharpe rose
from 0.511 (-127) to 0.923 (this iteration), SPY rose from 0.721 to 1.555
(now passes cleanly), and trade count dropped from 10-15 to 8 (fewer,
higher-conviction signals). However, QQQ still falls 0.077 short of the
1.0 Sharpe threshold, and the high-vol grid tercile remains decisively
0/24 -- the vol-regime EXIT filter reduces time spent in high-vol regimes
but doesn't prevent entries that turn sour as vol ramps up mid-trade.
Recorded as a near-miss worth a further iteration (e.g. also gating
ENTRY, not just exit, on the vol regime) rather than a decisive rejection.
