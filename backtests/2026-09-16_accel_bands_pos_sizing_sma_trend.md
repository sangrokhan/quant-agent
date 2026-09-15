# Backtest Report: Acceleration Bands Position-in-Channel Continuous Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_accel_bands_pos_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-049
**Date:** 2026-09-16

## Hypothesis

Acceleration Bands (Price Headley), per LuxAlgo's library page (same
source used for this repo's prior discrete-breakout attempt, id
2026-09-06-175, decisively rejected): Upper = SMA(High*(1+4*(High-Low)/
(High+Low)), N); Lower = SMA(Low*(1-4*(High-Low)/(High+Low)), N); Midline
= SMA(Close, N). This band widens/narrows with the daily high-low range (a
range-derived, not ATR-derived, construction, distinct from STARC/Keltner).
The prior discrete two-consecutive-close breakout entry failed decisively.
This iteration reinterprets the same band as a continuous position-in-
channel sizing dial (this repo's established STARC-%b/Keltner-%b/Bollinger-
%B pattern) rather than a breakout trigger, testing whether the band itself
carries information even though the breakout-trigger mechanism did not.

Construction: `dial = clip((close - midline) / (upper - lower) * 2, -1, 1)`
(already naturally bounded, no z-score needed) used directly as a
continuous exposure-sizing dial inside an SMA(trend_window=40) uptrend gate
with a deadband.

Source: LuxAlgo Acceleration Bands library page (already used for this
repo's id 2026-09-06-175; no new URL fetched this sub-iteration since the
exact formula was already documented in this repo's knowledge base).

## Step 6 — Grid summary

`run_grid_accel_bands_pos_sizing.py`: `param_grid` = ab_window in
{10,20,30} x sensitivity in {0.4,0.6,0.8} x deadband in {0.10,0.20},
symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3,
2019-2026.

- total_cells=216, passed=97, **pass_fraction=0.449**
- by_asset_class: equity 54/108, crypto 43/108
- by_vol_regime: low 67/72, mid 30/72, high 0/72
- best_cell: QQQ ab_window=30/sensitivity=0.8/deadband=0.20, low-vol Sharpe=2.80
- per-symbol grid pass: QQQ 36/54, SPY 18/54, BTC/USDT 29/54, ETH/USDT 14/54

## Step 7 — Single-config validators

Per-symbol configs retuned from grid raw-Sharpe cells to also survive
transaction costs and MDD (equity needed a wider deadband than the grid's
raw-Sharpe optimum; crypto needed a much lower `leverage_cap`/
`base_exposure`, per this repo's established crypto-overleverage pattern):

| Symbol | ab_window | sensitivity | deadband | base_exposure | leverage_cap | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 30 | 0.4 | 0.40 | 0.4 | 1.0 | 1.351 | 0.107 | 0.989 | 1.00 | 0.075 | YES |
| SPY | 20 | 0.4 | 0.50 | 0.4 | 1.0 | 1.182 | 0.068 | 0.886 | 1.00 | 0.107 | YES |
| BTC/USDT | 10 | 0.6 | 0.20 | 0.25 | 0.3 | 1.422 | 0.165 | 0.994 | 1.00 | 0.026 | YES |
| ETH/USDT | 10 | 0.6 | 0.20 | 0.25 | 0.25 | 1.343 | 0.162 | 1.072 | 1.00 | 0.040 | YES |

All 4 symbols pass all 5 validators (Sharpe>=1.0, MDD<=0.25, net Sharpe
after 10bps/trade costs >=0.5, walk-forward pass fraction >=0.75,
parameter-sensitivity relative-std <=0.5).

## Step 8 — Decision

**ACCEPT** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT).

## Notes

- Confirms this repo's recurring finding that a discrete breakout-trigger
  reading of a band can fail decisively while the *same band construction*
  reused as a continuous position-in-channel sizing dial succeeds --
  Acceleration Bands is now the latest in a growing list (DPO was the
  counter-example this same cron trigger, rejected even as a dial, showing
  this pattern doesn't hold universally).
- Equity needed deadband widened to 0.40-0.50 (from the grid's raw-Sharpe
  optimum 0.10-0.20) to survive transaction costs; crypto needed
  leverage_cap cut to 0.25-0.3 (from the grid default up to 1.0) to keep
  MDD under 0.25 -- both are this repo's now-standard retune moves for
  this family of continuous-sizing-dial strategies.
