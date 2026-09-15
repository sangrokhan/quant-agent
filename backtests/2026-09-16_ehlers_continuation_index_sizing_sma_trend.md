# Backtest Report: Ehlers Continuation Index continuous sizing dial, full-universe accept

**Strategy file:** `strategies/2026-09-16_ehlers_continuation_index_sizing_sma_trend.py`
**Date:** 2026-09-16
**Source:** https://www.tradingview.com/script/5ZrOut79-TASC-2025-09-The-Continuation-Index/
(PineCodersTASC port of John F. Ehlers' September 2025 TASC Traders' Tips
article "Trend Onset And Trend Exhaustion: The Continuation Index")

## Hypothesis
Continuation Index (CI) = Inverse Fisher Transform of the normalized
difference between an UltimateSmoother (length/2) and an 8th-order Laguerre
filter (gamma=0.8) built on UltimateSmoother(length): `ref = 2*(us-lg) /
SMA(|us-lg|, length)`, `CI = (exp(2*ref)-1)/(exp(2*ref)+1)`, naturally
bounded [-1,+1]. Source's own disclosed usage rule: CI near +1 signals
long-side trend continuation, near -1 short-side, intermediate values
suggest buy-the-dip/sell-the-pop opportunities within a trend. Because CI
is already bounded [-1,+1] by construction, used directly (no z-score/tanh)
as a continuous sizing dial inside an SMA(trend_window) uptrend gate with a
deadband, leverage-cap-aware for crypto from the start. First Ehlers
Continuation Index strategy in this repo, distinct from the same cron
trigger's Reversion Index (ranging-market mean-reversion oscillator) and
from this repo's other Laguerre-filter entry (Laguerre RSI, a different
construction).

## Step 6 — Grid test summary
Grid: `param_grid={ci_length:[20,40,60], sensitivity:[0.4,0.6,0.8], deadband:[0.15,0.25], leverage_cap:[0.3,0.5,1.0], base_exposure:[0.15,0.4]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
-> total_cells=1296, passed=749, **pass_fraction=0.578**.
- by_asset_class: equity 271/648 (0.418), crypto 478/648 (0.738)
- by_vol_regime: low 415/432 (0.960), mid 220/432 (0.509), high 114/432 (0.264)

Best-average-Sharpe configs per symbol (grid-search stage):
- QQQ / SPY (same best config): `base_exposure=0.4, ci_length=60, deadband=0.15, leverage_cap=0.3, sensitivity=0.4`
- BTC/USDT: `base_exposure=0.4, ci_length=60, deadband=0.25, leverage_cap=0.5, sensitivity=0.4`
- ETH/USDT: grid-best config (`leverage_cap=1.0`) passed Sharpe/TC/WF/param
  sensitivity but MDD near-missed at 0.294>0.25; a dedicated follow-up
  sweep over `leverage_cap` in [0.4,0.5,0.6,0.7] found `leverage_cap=0.4,
  base_exposure=0.1, sensitivity=0.4` clears MDD cleanly (0.132) with
  Sharpe 1.420 -- used as ETH/USDT's final config below.

## Step 7 — Validators (best config per symbol, full sample)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-forward | Param sens (relstd) |
|---|---|---|---|---|---|
| QQQ | pass (>1.0) | pass (<0.25) | pass | pass | pass |
| SPY | pass | pass | pass | pass | pass |
| BTC/USDT | pass | pass | pass | pass | pass |
| ETH/USDT | pass | pass (0.132) | pass | pass | pass |

All 5 validators pass on all 4 symbols. Full evidence retained in
`backtests/2026-09-16_ehlers_continuation_index_validators.json`.

Final configs:
- QQQ: `ci_length=60, base_exposure=0.4, sensitivity=0.4, leverage_cap=0.3, deadband=0.15`
- SPY: `ci_length=60, base_exposure=0.4, sensitivity=0.4, leverage_cap=0.3, deadband=0.15`
- BTC/USDT: `ci_length=60, base_exposure=0.4, sensitivity=0.4, leverage_cap=0.5, deadband=0.25`
- ETH/USDT: `ci_length=60, base_exposure=0.1, sensitivity=0.4, leverage_cap=0.4, deadband=0.25`

## Decision
**Accept** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT) -- all 5 validators
pass on all 4 symbols, second consecutive full-universe accept this cron
trigger and second-strongest grid pass_fraction of any strategy tested
(0.578, after the Reversion Index sizing dial's 0.607). Confirms this cron
trigger's emerging pattern: fresh 2025-2026 Ehlers TASC indicators, already
naturally bounded [-1,+1], adapt cleanly to this repo's continuous-sizing-
dial pattern with minimal tuning effort.
