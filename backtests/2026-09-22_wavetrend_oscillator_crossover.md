# WaveTrend Oscillator Crossover (Backtest Report — REJECTED)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_wavetrend_oscillator_crossover.py`
**KB id:** 2026-09-22-008

## Hypothesis

Per LazyBear's disclosed Pine Script source for the WaveTrend Oscillator
[WT_LB]
(https://github.com/bnvnvnv/fmzstrategies/blob/master/Indicator-WaveTrend-Oscillator.md):
ap=(H+L+C)/3, esa=EMA(ap,n1), d=EMA(|ap-esa|,n1), ci=(ap-esa)/(0.015*d),
tci=EMA(ci,n2), wt1=tci, wt2=SMA(wt1,4). Long entry: wt1 crosses above wt2
while below the oversold band (-60/-53); exit on cross back below wt2 or
climbing above the overbought band (+60), or a time-stop. First test of
WaveTrend in this repo (0 prior KB hits).

## Grid test summary (Step 6)

`param_grid={os_level1:[-53.0,-60.0], max_hold_days:[15,20,30]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3` → 72 cells total.

- **Overall pass_fraction: 0.0 (0/72) -- decisive rejection, no cell
  cleared the Sharpe/MDD bar in any asset class or vol regime.**
- By asset class: equity 0/36, crypto 0/36
- By vol regime: low 0/24, mid 0/24, high 0/24
- Best cell: QQQ, os_level1=-53.0, max_hold_days=20, low-vol, Sharpe=0.758
  (still below the 1.0 threshold)
- Worst cell: SPY, os_level1=-53.0, max_hold_days=20, mid-vol,
  Sharpe=-1.373
- SPY mid-vol cells were consistently strongly negative (-0.76 to -1.37)
  across every parameter combo tested -- a systematic, not incidental,
  failure mode for this symbol/regime.

## Decision

**Reject, no single-config validation attempted.** The grid result is
decisive (0/72 cells pass) with no promising region in any asset
class/vol-regime combination to focus a Step 7 single-config validation
on -- per RESEARCH_LOOP.md Step 8, a strategy failing this comprehensively
in the grid stage does not warrant proceeding to the full validator suite.
The mean-reversion-style "buy near oversold, exit near overbought"
long-only framing of this indicator (chosen because this repo doesn't
implement short strategies) evidently does not translate into a durable
edge on daily QQQ/SPY/BTC/ETH bars at the tested parameterizations.
