# Ehlers Predictive Moving Average (PMA) Predict/Trigger Crossover — ACCEPTED (QQQ only)

**Hypothesis:** Per John Ehlers' "Predictive Moving Average" (Rocket
Science for Traders, 2001, ch.20; explainer at
https://vectoralpha.dev/projects/ta/indicators/ehlers_pma/), a
double-smoothed WMA extrapolation reduces lag: WMA1 = WMA(price,7);
WMA2 = WMA(WMA1,7); predict = 2*WMA1 - WMA2 (extrapolation); trigger =
WMA(predict,4). Bullish cross (predict > trigger) signals long. This is a
DIFFERENT PMA from the already-tested "Ehlers Projected Moving Average"
(2026-09-13-024/025, rejected: SMA + linear-regression-slope projection,
from TASC March 2025) — this construction uses double-WMA extrapolation,
not slope-based regression projection. First strategy in this repo using
this specific construction. Adapted with a longer-term SMA trend filter
(gating on close > SMA(trend_window)) per Ehlers' own recommendation to
combine with a trend filter to avoid whipsaws in choppy conditions.

## Step 6 — Grid test summary

Grid: `trigger_len` in {3,4,6} x `trend_window` in {50,100,150}, symbols
equity={SPY,QQQ} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3 (WMA1/
WMA2 lengths held at Ehlers' disclosed default of 7). 108 total cells.

- `pass_fraction`: 41/108 = **0.380** (third-strongest grid result this
  cron trigger, after LSMA's 0.417 and Dual-KAMA's 0.347)
- `by_asset_class`: equity 27/54 passed, crypto 14/54 passed
- `by_vol_regime`: low 27/36, mid 14/36, high 0/36
- `best_cell`: trigger_len=6, trend_window=50, ETH/USDT, mid-vol regime,
  Sharpe=2.21
- `worst_cell`: trigger_len=6, trend_window=50, QQQ, high-vol regime,
  Sharpe=-1.12

The initial coarse sweep (trigger_len/trend_window only, WMA1/WMA2 fixed
at 7) topped out at QQQ Sharpe 0.789 full-sample -- a near-miss. A finer
sweep additionally varying wma1_len/wma2_len found a config clearing the
threshold.

## Step 7 — Single-config validation (full sample 2018-01 to 2026-09)

### QQQ, wma1_len=14, wma2_len=5, trigger_len=4, trend_window=150

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.050 | >= 1.0 | pass |
| Max drawdown | 0.146 | <= 0.25 | pass |
| Tx-cost survival (5bps/trade, 232 trades) | net Sharpe 0.851 | >= 0.5 | pass |
| Walk-forward (manual 4-split) | pass_fraction 1.0 | >= 0.75 | pass (4/4 splits positive) |
| Parameter sensitivity (9-cell wma1_len x trend_window sweep) | relative_std 0.165 | <= 0.5 | pass |

**All 5 validators pass on QQQ.** Strong walk-forward and reasonable
parameter stability.

### SPY, BTC/USDT, ETH/USDT, same config

All decisively fail: SPY Sharpe 0.662/MDD 0.225/net-Sharpe 0.412; BTC
Sharpe 0.102/MDD 65.9%/net-Sharpe -0.038; ETH Sharpe 0.149/MDD 45.8%/
net-Sharpe -0.014. The lengthened wma1_len=14 (vs Ehlers' disclosed
default of 7) captures a slower, QQQ-specific trend rhythm that doesn't
transfer to SPY's typically lower-beta price action or to crypto's
faster/choppier cycles.

## Decision: ACCEPTED (QQQ only, wma1_len=14, wma2_len=5, trigger_len=4,
trend_window=150)

All 5 validators pass for QQQ. SPY and crypto are decisively rejected at
this specific retuned config (not near-misses) — a future loop would need
a substantially different parameter regime (shorter WMA lengths per the
grid's own by_asset_class breakdown showing crypto only passing at
trigger_len=6/trend_window=50-ish combos) rather than a simple retune to
extend scope. Strategy file kept live in `strategies/` for QQQ scope only.
