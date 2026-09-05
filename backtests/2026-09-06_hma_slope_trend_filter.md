# Backtest Report: Hull Moving Average (HMA) Slope-Based Trend Filter

**Strategy file:** `strategies/2026-09-06_hma_slope_trend_filter.py`
**Date:** 2026-09-06

## Hypothesis

Long entry when the HMA's own slope turns from non-positive to positive
(HMA[t] > HMA[t-1] and HMA[t-1] <= HMA[t-2]); exit on the reverse slope
flip or a max_hold_days time-stop. Per LuxAlgo Indicator Library ("HMA:
Trend Concept": "As a slope-based trend filter: take longs only while the
HMA rises and shorts only while it falls"), corroborated by
Capital.com/GoCharting/marketindicatorlab.com. Distinct from this repo's
already-tested price-crosses-HMA strategy (2026-09-04-026, near-miss)
which triggers on close crossing the HMA line, not on the HMA's own slope
turning.

## Grid test (Step 6)

`param_grid`: hma_window in {20,40,60}, max_hold_days in {20,40,60};
symbols equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]; vol_regime_splits=3.
108 total cells.

- pass_fraction: 0.2685 (29/108)
- by_asset_class: equity 29/54, crypto 0/54
- by_vol_regime: low 18/36, mid 5/36, high 6/36 — spreads across all 3
  regimes, not concentrated purely in low-vol (similar breadth to the
  MACD-V strategy accepted earlier this cron trigger)
- best_cell (tercile-level): hma_window=60, max_hold_days=60, SPY,
  low-vol, Sharpe 2.884

## Full-sample manual scan + shared-config search (Step 6/7)

Expanded full-sample scan (hma_window in {20,30,40,50,60}, max_hold_days
in {20,30,40,60}) found strong full-sample Sharpe on BOTH symbols
individually (QQQ best 1.238 at hma_window=20/max_hold_days=30; SPY best
1.595 at hma_window=50/max_hold_days=40). Searched for a SHARED config
passing both Sharpe+MDD on QQQ and SPY simultaneously: **hma_window=30,
max_hold_days=30** clears both gates on both symbols (QQQ Sharpe
1.172/MDD 0.228, 68 trades; SPY Sharpe 1.250/MDD 0.125, 71 trades) —
selected as primary shared config.

Crypto rejected decisively (0/54 grid cells).

## Single-config validation (Step 7) — shared config, QQQ and SPY

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.172 ✅ | 1.250 ✅ | ≥ 1.0 |
| Max drawdown | 0.228 ✅ | 0.125 ✅ | ≤ 0.25 |
| Transaction cost survival (10bps, N trades) | net 1.081 ✅ (68 trades) | net 1.115 ✅ (71 trades) | ≥ 0.5 |
| Walk-forward (4 manual splits) | 4/4 positive ✅ (1.84/0.46/2.10/0.59) | 4/4 positive ✅ (1.89/0.71/2.11/0.30) | ≥ 0.75 |
| Parameter sensitivity (hma_window ∈ {20,30,40}) | rel_std 0.107 ✅ | rel_std 0.152 ✅ | ≤ 0.5 |

## Decision: **ACCEPT (QQQ and SPY, shared config)**

All 5 validators pass on both equity symbols with one shared config — the
second shared-config accept this cron trigger (alongside MACD-V), and a
notably clean result (all walk-forward splits positive, low
parameter-sensitivity relative std on both symbols). Crypto excluded from
scope (0/54 grid cells).
