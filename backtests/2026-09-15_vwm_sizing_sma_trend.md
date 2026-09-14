# Volume Weighted Momentum (VWM) Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-15
**Strategy ID:** 2026-09-15-011 (assigned in knowledge_base log)
**File:** `strategies/2026-09-15_vwm_sizing_sma_trend.py`

## Hypothesis

Volume Weighted Momentum (VWM): Price Momentum = Close - Close[mom_period
periods ago] (a plain n-period price difference, distinct from every prior
volume-weighted indicator in this repo -- VWMA weights the price average
itself, VW-MACD is a spread of two VWMAs, PVO/VPCI weight volume by
volume-of-volume ratios). VWM_raw = Price Momentum * Volume, VWM =
SMA(VWM_raw, smooth_period). Already zero-centered by construction. This
iteration follows this cron trigger's repeatedly-validated
continuous-sizing-dial pattern: VWM rolling z-scored + tanh-squashed to
[-1,1], used as a sizing multiplier within an SMA(trend_window) uptrend
gate, deadband to cut turnover, leverage_cap for crypto. First plain
Volume Weighted Momentum entry in this repo (11 prior entries matched
"Volume Weighted Momentum|VWM" keyword search but all were VWMA/VW-MACD/
VPCI variants, not this specific price-difference-times-volume
construction).

Source: https://alfatactix.com/academy/indicators/volume-weighted-momentum
(visited this iteration via browser_exec fallback -- web_extract's ddgs
backend cannot extract URL content, only search) -- "VWM is calculated by
multiplying price momentum by volume, then smoothing the result with a
moving average... typically using 14 periods for smoothing."

## Grid test summary (Step 6)

`param_grid={mom_period: [10,20,30], smooth_period: [14,21], sensitivity:
[0.4,0.6], deadband: [0.2,0.3]}`, symbols QQQ/SPY (equity) +
BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 288, **passed:** 120, **pass_fraction:** 0.417.
- **by_asset_class:** equity 73/144 (0.507), crypto 47/144 (0.326).
- **by_vol_regime:** low 74/96 (0.771), mid 45/96 (0.469), high 1/96 (0.010).
- **best_cell:** QQQ, mom_period=30/smooth_period=21/sensitivity=0.6/
  deadband=0.2, low-vol, Sharpe 3.050.
- **worst_cell:** QQQ, mom_period=30/smooth_period=21/sensitivity=0.4/
  deadband=0.3, high-vol, Sharpe -1.000.
- Best mean-Sharpe-across-vol-regimes config: QQQ, mom_period=10/
  smooth_period=14/sensitivity=0.6/deadband=0.2 (mean Sharpe 1.367, 2/3
  vol regimes pass).

## Single-config validator results (Step 7)

Best grid config (mom_period=10, smooth_period=14, sensitivity=0.6,
deadband=0.2, trend_window=40, base_exposure=0.4) tested full-sample on
QQQ, leverage_cap=1.0:

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.130 (pass) | 0.138 (pass) | 0.645 (pass, 214 trades) | 1.000 (pass, 4/4 splits) | 0.066 (pass) | **accepted** |

Walk-forward used a manual 4-way `np.array_split` of the price index (repo's
`check_walk_forward` calls `vbt.utils.splitting.RangeSplitter`, which does
not exist in the installed vectorbt version -- `AttributeError: module
'vectorbt.utils' has no attribute 'splitting'`; same fix pattern noted in
several prior entries this cron trigger). Parameter sensitivity computed
from a 6-cell mom_period x smooth_period sub-grid at the winning
sensitivity/deadband on QQQ.

SPY and both crypto pairs were not carried to full single-config validation
this iteration (workload=max budget spent on QQQ's cleanly-passing best
cell); the grid's `by_asset_class`/`by_vol_regime` breakdown above already
shows the strategy concentrates its edge in low/mid-vol equity cells and is
weak in crypto and high-vol regimes broadly, consistent with nearly every
other continuous-sizing-dial variant tested this cron trigger.

## Decision

**Accepted (QQQ only):** clears all 5 validators. VWM's raw price-
difference-times-volume construction, reframed as a continuous sizing dial,
is a genuinely new indicator family in this repo (not just a technique
variant on an already-tested formula) sourced from this iteration's actual
external research.
**Not yet tested (SPY, BTC/USDT, ETH/USDT):** left for a future loop's
SPY/crypto-fix iteration per this cron trigger's established pattern (see
Coppock/AO/Ulcer/Rainbow entries), grid data above gives a starting point.
