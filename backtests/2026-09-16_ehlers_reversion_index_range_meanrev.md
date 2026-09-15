# Backtest Report: Ehlers Reversion Index (TASC Jan 2026) range mean-reversion

**Strategy file:** `strategies/2026-09-16_ehlers_reversion_index_range_meanrev.py`
**Date:** 2026-09-16
**Source:** https://www.tradingview.com/script/V35NeC45-TASC-2026-01-The-Reversion-Index/
(PineCodersTASC port of John F. Ehlers' January 2026 TASC Traders' Tips
article "Identifying Peaks And Valleys In Ranging Markets")

## Hypothesis
Raw Reversion Index (RI) = rolling-window net price change normalized by
the rolling-window sum of absolute price changes (bounded [-1,+1]), then
Ehlers' 2-pole SuperSmoother applied at two periods: `Smooth` (period 8)
and `Trigger` (period 4, leads Smooth). Ehlers' own disclosed rule: Trigger
crossing above Smooth marks a valley (buy), crossing below marks a peak
(sell). Long-only, entered only when price is within a cheap OHLCV-only
"ranging, not trending" proxy band (per Ehlers' explicit design note that
this indicator targets ranging markets, not trending ones), with a
`max_hold_days` time-stop backstop. First Ehlers Reversion Index /
net-change-ratio-normalized-then-SuperSmoothed oscillator in this repo.

## Step 6 — Grid test summary
Grid: `param_grid={ri_length:[10,20,30], range_band_pct:[0.3,0.5], max_hold_days:[10,20]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
-> total_cells=144, passed=50, **pass_fraction=0.347**.
- by_asset_class: equity 36/72 (0.50), crypto 14/72 (0.194)
- by_vol_regime: low 38/48 (0.79), mid 4/48 (0.083), high 8/48 (0.167)

## Step 7 — Validators (best-average-Sharpe config per symbol, full sample)

Initial grid-best configs (`ri_length=20, max_hold_days=20, range_band_pct=0.3`
equity / `max_hold_days=10` crypto):

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sens |
|---|---|---|---|---|---|
| QQQ | 0.834 (**fail**, <1.0) | 0.199 (pass) | pass | pass | **fail** |
| SPY | 0.981 (**fail**, <1.0, near-miss) | 0.160 (pass) | pass | pass | **fail** |
| BTC/USDT | 1.285 (pass) | 0.509 (**fail**, >0.25) | pass | pass | pass |
| ETH/USDT | 1.016 (pass) | 0.658 (**fail**, >0.25) | pass | pass | pass |

Followed up with a wider dedicated per-symbol parameter search
(`ri_length` in [10,15,20,25,30,40], `max_hold_days` in [5,8,10,15,20,25],
`range_band_pct` in [0.2,0.3,0.4,0.5]) to look for a rescue config:
- QQQ best full-sample Sharpe found: **0.918** (ri_length=20, max_hold_days=8,
  range_band_pct=0.2) -- still below the 1.0 threshold.
- SPY best: **0.981** (ri_length=20, max_hold_days=20, range_band_pct=0.2) --
  same near-miss ceiling as the grid-best config, no improvement found.
- BTC/USDT: best Sharpe 1.331 (ri_length=20, max_hold_days=5, range_band_pct=0.15)
  still carries MDD ~0.498 -- no combination in a 3x4x3 dedicated crypto
  sweep cleared both Sharpe>1.0 AND MDD<0.25 simultaneously (this is a
  binary 0/1-exposure strategy with no position-sizing overlay, so full
  100% exposure on crypto's raw volatility structurally produces >2x the
  MDD threshold, consistent with several other pure-signal strategies this
  cron trigger before a vol-targeting overlay rescue).
- ETH/USDT: best Sharpe 1.132 (ri_length=20, max_hold_days=5,
  range_band_pct=0.15), MDD ~0.626 -- same structural MDD problem.

## Decision
**Reject** (all 4 symbols). Equity (QQQ, SPY) both hit a Sharpe ceiling
around 0.92-0.98 across a fairly wide parameter search -- a near-miss but
consistently below the 1.0 bar, unlike several other near-misses this cron
trigger that a wider search cleared. Crypto (BTC/USDT, ETH/USDT) pass Sharpe
comfortably but decisively fail max-drawdown (~2x the 0.25 threshold) at
full binary exposure -- the same "needs an inverse-vol/vol-targeting sizing
overlay" pattern already fixed for several other strategies this cron
trigger (Coral Trend, HalfTrend, CTI, TPR). Recorded as a near-miss worth
revisiting: a follow-up sub-iteration could (a) retest equity with a
continuous-sizing-dial reframing of the RI value itself (already bounded
[-1,1] like several accepted continuous-sizing entries) instead of a binary
crossover-with-time-stop signal, and (b) apply the repo's established
inverse-volatility position-sizing overlay to fix crypto's MDD, matching the
pattern that rescued Coral Trend/HalfTrend/CTI/TPR earlier this cron trigger.
