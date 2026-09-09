# Backtest Report: Detrended Synthetic Price Zero-Cross, ITL Slope Confirm (QQQ)

**Strategy file:** `strategies/2026-09-09_dsp_zerocross_itl_slope.py`
**Date:** 2026-09-09

## Hypothesis + Source

Per AlphaX Trading's Detrended Synthetic Price dictionary entry
(https://alphax.trading/dictionary/detrended-synthetic-price, browser_exec
fallback -- web_search DDGS errored/returned no results for the direct
query), DSP = Price - Instantaneous Trendline (an Ehlers-style recursive
high-pass filter). Source's execution rules: long entry on DSP crossing
above zero with the Instantaneous Trendline sloping upward, gated by a
200-SMA trend filter and a "not stagnant" filter to avoid flat/near-zero
DSP conditions. Distinct from all 4 existing repo DPO strategies, which
use the simpler shifted-SMA-based Detrended Price Oscillator formula, not
an Ehlers instantaneous-trendline construction.

## Single-config metrics (QQQ, filter_period=25, max_hold_days=10,
2018-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | Yes | 1.177 | >= 1.0 |
| Max drawdown | Yes | 6.39% | <= 25% |
| Transaction cost survival (10bps/trade, 68 trades) | Yes | 0.949 | >= 0.5 |
| Walk-forward (4 manual date-slice splits) | Yes | 1.0 (4/4 positive) | >= 0.75 |
| Parameter sensitivity (filter_period in [20,22,25,28,30]) | Yes | rel.std 0.096 | <= 0.5 |

All 5 validators pass for QQQ at this config.

## Step 6 grid summary

Grid (scoped smaller per `suggested_workload=normal` for this iteration):
`filter_period=[15,20,30]` x `max_hold_days=[15,25]`, symbols
QQQ/SPY/BTC-USDT/ETH-USDT, `vol_regime_splits=3`, 2018-2026.

- Overall pass_fraction: 0.236 (17/72 cells)
- By asset class: equity 17/36, crypto 0/36 (crypto decisively fails)
- By vol regime: low 12/24, mid 5/24, high 0/24
- Best cell: filter_period=30/max_hold_days=25, QQQ, low-vol regime,
  Sharpe 1.716
- A fine-grained search beyond the initial grid found QQQ
  filter_period=25/max_hold_days=10 as the best full-sample config
  (Sharpe 1.177). SPY at its own best full-sample config only reaches
  0.179 -- rejected for SPY.
- Crypto (BTC/USDT, ETH/USDT): 0/36 cells passed -- decisively rejected.

## Pass/Fail per validator

All 5 validators pass for the QQQ config above. SPY and crypto (BTC/USDT,
ETH/USDT) are rejected.

## Outcome

**Accepted for QQQ only** (filter_period=25, max_hold_days=10). Rejected
for SPY and crypto (BTC/USDT, ETH/USDT).
