# Ehlers Detrended Synthetic Price (DSP) Slope Color-Change — Backtest Report

**Date:** 2026-09-05
**Strategy file:** `strategies/2026-09-05_dsp_slope_colorchange.py`
**KB id:** 2026-09-05-065

## Hypothesis

Per https://stonehillforex.com/2023/01/detrended-synthetic-price-as-a-confirmation-indicator/:
John Ehlers' Detrended Synthetic Price (DSP, Stocks & Commodities July 2000)
highlights the dominant price cycle: `DSP = EMA(median_price, period/4) -
EMA(median_price, period/2)`. Source's own rule: long when the signal
"turns green" (DSP starts rising), exit/short when it "turns red" (DSP
falling) or "gray" (flat -- noted as a possible exit zone). First DSP
strategy in this repo.

## Step 6 — Grid test (dsp_period x max_hold_days x QQQ/SPY/BTC/ETH x 3 vol regimes)

- param_grid: `dsp_period=[10,14,20]`, `max_hold_days=[10,15,25]`
- symbols: equity `[QQQ, SPY]`, crypto `[BTC/USDT, ETH/USDT]`
- vol_regime_splits=3
- **108 total cells, 21 passed (pass_fraction = 0.194)**
- by_asset_class: equity 21/54; **crypto 0/54 (decisive fail)**
- by_vol_regime: low 18/36; mid 3/36; **high 0/36 (decisive fail)**
- best_cell: QQQ, dsp_period=20/max_hold_days=10, low-vol regime, Sharpe=3.21
- worst_cell: QQQ, dsp_period=14/max_hold_days=10, high-vol regime, Sharpe=-0.47
- Best full-regime-coverage config: QQQ dsp_period=14/max_hold_days=10 (2/3 regimes pass: low 2.45, mid 1.12, high fails -0.47)

## Step 7 — Single-config validators (dsp_period=14, max_hold_days=10)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full period) | 0.42 — FAIL | 0.33 — FAIL | >= 1.0 |
| Max drawdown | 0.373 — FAIL | 0.291 — FAIL | <= 0.25 |
| Transaction cost survival (10bps/trade, ~340/336 trades) | 0.08 — FAIL | -0.05 — FAIL | net Sharpe >= 0.5 |
| Walk-forward (4-split, manual fallback) | 0.50 — FAIL | 0.75 — PASS | >= 0.75 |
| Parameter sensitivity | 0.384 — PASS | 0.348 — PASS | <= 0.5 |

The grid's eye-catching low-vol-only Sharpe (up to 3.21) does not survive
unconditional full-period testing on either symbol: very high trade
frequency (~340 round trips over the sample, driven by the color-change
rule firing on nearly every short-term slope flip) crushes returns once
transaction costs are applied (net Sharpe near zero or negative), and
drawdown far exceeds the 25% threshold on both symbols.

## Step 8 — Decision: **REJECT**

Decisive rejection: Sharpe, max drawdown, and transaction-cost survival
all fail on both QQQ and SPY; only parameter sensitivity passes. Crypto is
a decisive 0/54 grid fail. Strategy/report kept as a record of a rejected
attempt — this is NOT a live strategy.
