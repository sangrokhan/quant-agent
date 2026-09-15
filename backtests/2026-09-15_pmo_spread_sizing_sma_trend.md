# Backtest Report: PMO Spread Continuous Sizing Dial (SMA Trend Gate)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_pmo_spread_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-045

## Hypothesis

DecisionPoint Price Momentum Oscillator (PMO, Carl Swenlin), formula
already documented in this repo from prior iteration 2026-09-05-010
(re-confirmed via this cron trigger's search of stockmaniacs.net /
chartschool.stockcharts.com, sources not re-fetched per dedupe ledger): a
double-smoothed 1-period ROC oscillator using a non-standard EMA smoothing
factor (2/length instead of 2/(length+1)) -- daily pct-change*10 smoothed
over a 35-period window, smoothed again over a 20-period window (PMO
Line), with a 10-period EMA of PMO Line forming the Signal Line. This
repo's prior PMO entry (2026-09-05-010) used a discrete PMO-crosses-Signal
trigger and was decisively rejected across all asset classes. This
iteration reuses the identical double-smoothed-ROC construction as a
CONTINUOUS sizing dial: the PMO-minus-Signal spread is rolling z-scored
and tanh-squashed into [-1,+1], used inside an SMA(trend_window) uptrend
gate with a deadband.

## Step 6 — Grid summary (signal_window x sensitivity, 2 asset classes x 3 vol terciles)

- Grid: `signal_window in [7, 10, 15]`, `sensitivity in [0.5, 0.8]`,
  symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
  `vol_regime_splits=3`.
- **72 cells, 37 passed (pass_fraction = 0.514)**.
- By asset class: equity 20/36, crypto 17/36.
- By vol regime: low 24/24 (perfect), mid 7/24, high 6/24.
- Best cell: QQQ, signal_window=15, sensitivity=0.5, low-vol regime,
  Sharpe 2.56.
- Worst cell: SPY, signal_window=10, sensitivity=0.8, mid-vol regime,
  Sharpe -0.01.

## Step 7 — Single-config validator suite (per-asset-class retuned)

Equity config: `signal_window=15, roc_smooth1=35, roc_smooth2=20,
sensitivity=0.5, trend_window=40, zscore_window=100, base_exposure=0.4,
leverage_cap=1.0, deadband=0.5`.
Crypto config (leverage-cap-aware retune): same core, `base_exposure=0.24,
leverage_cap=0.4, deadband=0.25`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass | Param sensitivity (rel std) | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.313 (pass) | 0.106 (pass) | 1.143 (pass) | 1.00 (pass) | 0.020 (pass) | **Yes** |
| SPY | 1.224 (pass) | 0.078 (pass) | 1.013 (pass) | 0.75 (pass) | 0.098 (pass) | **Yes** |
| BTC/USDT | 1.436 (pass) | 0.223 (pass) | 1.248 (pass) | 0.75 (pass) | 0.033 (pass) | **Yes** |
| ETH/USDT | 1.234 (pass) | 0.175 (pass) | 1.125 (pass) | 1.00 (pass) | 0.093 (pass) | **Yes** |

Walk-forward used the repo's established manual 4-equal-slice fallback.

## Step 8 — Decision: **ACCEPT (full universe: QQQ, SPY, BTC/USDT, ETH/USDT)**

All four symbols pass all 5 validators with strong margins (Sharpe
1.22-1.44 throughout) and very tight parameter-sensitivity (rel std
0.02-0.10, tightest of this cron trigger's iterations). This is the third
full-universe accept of this cron trigger's 7 iterations (after PVI and
RVI), rescuing 2026-09-05-010's decisive rejection entirely via the
continuous-sizing-dial transform.
