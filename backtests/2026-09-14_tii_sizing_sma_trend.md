# Trend Intensity Index (TII) Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-175 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_tii_sizing_sma_trend.py`
**Status:** REJECTED (all 4 symbols, QQQ/SPY both near-miss) -- kept as a
record per Step 8.

## Hypothesis

Trend Intensity Index (TII): major_sma=SMA(close,major_period);
deviation=close-major_sma; sdpos/sdneg=rolling sums of positive/negative
deviations over minor_period; TII=100*sdpos/(sdpos+sdneg), bounded [0,100],
centered at 50. Reused verbatim from this repo's 3 prior confirmed TII
entries, all binary midline-cross/extreme-threshold/breakout triggers. This
iteration reframes TII as a CONTINUOUS SIZING dial: since TII is already
bounded [0,100], directly rescale via (TII-50)/50 -> [-1,1] WITHOUT an
additional z-score/tanh stage (unlike unbounded oscillators used earlier
this cron trigger). First TII continuous-sizing variant in this repo.

Source: repo's own prior confirmed formula (2026-09-04/05/08 TII entries);
no new external source needed.

## Grid test summary (Step 6)

`param_grid={minor_period: [10,20], sensitivity: [0.4,0.6,0.8]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 26, **pass_fraction:** 0.361.
- **by_asset_class:** equity 18/36 (0.500), crypto 8/36 (0.222).
- **by_vol_regime:** low 18/24 (0.750), mid 8/24 (0.333), high 0/24 (0.000).
- **best_cell:** QQQ, minor_period=10/sensitivity=0.4, low-vol, Sharpe
  2.770.
- **worst_cell:** QQQ, minor_period=20/sensitivity=0.4, high-vol, Sharpe
  -0.821.

## Single-config validator results (Step 7)

Best grid config (minor_period=10, sensitivity=0.4) tested full-sample per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 0.978 (**fail**, near-miss) | 0.153 (pass) | 0.599 (pass) | 0.750 (pass) | 0.087 (pass) | **rejected** |
| SPY | 0.954 (**fail**, near-miss) | 0.094 (pass) | 0.511 (pass) | 0.750 (pass) | 0.062 (pass) | **rejected** |
| BTC/USDT | 0.159 (**fail**, decisive) | 0.233 (pass) | -0.061 (**fail**) | 1.000 (pass) | 0.048 (pass) | **rejected** |
| ETH/USDT | 0.177 (**fail**, decisive) | 0.264 (**fail**) | -0.055 (**fail**) | 1.000 (pass) | 0.075 (pass) | **rejected** |

## Decision

**Rejected (all 4 symbols).** QQQ and SPY BOTH near-miss Sharpe (0.978 and
0.954 vs 1.0 threshold) while clearing every other validator comfortably
(MDD, TC-survival, walk-forward, parameter sensitivity all pass) -- unlike
most other rejections this cron trigger which fail decisively on multiple
fronts, this is a genuine close-call double near-miss worth flagging for a
future loop's direct-fix attempt (e.g. tuning major_period/trend_window or
widening sensitivity slightly). Crypto fails Sharpe/TC-survival decisively
as usual for daily-bar-calibrated sizing dials. Recorded as a near-miss
rather than a decisive rejection so a future iteration can attempt the
established "direct fix" pattern (parameter re-sweep targeting the specific
near-miss metric) already used successfully elsewhere in this repo (e.g.
Klinger Volume Oscillator 2026-09-04-085, Vortex SPY fix 2026-09-11-107).
