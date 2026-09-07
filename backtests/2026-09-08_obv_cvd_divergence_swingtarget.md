# Backtest Report: OBV Cumulative-Delta-Proxy Divergence, Swing Target/Stop

**Strategy file:** `strategies/2026-09-08_obv_cvd_divergence_swingtarget.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Per pinescriptforge.com's Cumulative Delta Divergence strategy
(https://pinescriptforge.com/strategy/cumulative-delta-divergence, backtested
by the source across 64 futures symbols with mixed but often-positive Sharpe):
"price makes a lower low while cumulative delta makes a higher low" (bullish
divergence) signals absorption of selling pressure, target = prior swing
high, stop = beyond the divergence pivot. This repo has no tick-level
buy/sell-aggressor volume, so OBV (cumulative directional volume by daily
close sign) is used as the closest available proxy for cumulative delta.
Distinct from 2026-09-04-088 (rejected OBV divergence, required an EMA
confirmation cross before entry, fixed-stop exit) via using immediate
confirmation-bar entry and the source's own swing-pivot target/stop.

## Grid test summary (Step 6)

`pivot_window` in [5,10] x `stop_atr_mult` in [1.0,1.5] x `max_hold_days` in
[15,20], symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01..2026-09-01.

- total_cells: 96, passed_cells: 4, **pass_fraction: 0.042**
- by_asset_class: equity 4/48, crypto **0/48** (decisive)
- by_vol_regime: low 0/32, **mid 4/32**, high 0/32
- All passing cells: QQQ, mid-vol-regime, pivot_window=5 only (pivot_window=10
  produced zero passing cells at all -- longer swing-pivot detection window
  found no qualifying divergences in that regime)
- Sharpe identical (1.387) across stop_atr_mult/max_hold_days values in the
  mid-vol passing cells, suggesting the target (not the stop or time-stop)
  is what's actually triggering exits in that slice -- i.e. very few trades,
  none testing the stop/hold boundary.

## Single-config validators (Step 7): QQQ, pivot_window=5, stop_atr_mult=1.0,
max_hold_days=15, full sample 2018-01-01..2026-09-01

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full sample) | ❌ | 0.663 | ≥ 1.0 |
| max_drawdown | ✅ | 0.005 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 4 trades) | ✅ | net Sharpe 0.574 | ≥ 0.5 |

Skipped walk-forward / parameter-sensitivity: only **4 total round-trip
trades** over the entire 8.7-year sample -- statistically insufficient to
draw any conclusion regardless of Sharpe/MDD values (consistent with this
repo's established pattern of treating <~10 trades as inconclusive, e.g.
2026-09-05-013's RMI rejection for the same reason).

## Decision: REJECT

Bullish OBV-divergence-as-cumulative-delta-proxy signals are extremely rare
on daily bars (4 trades on QQQ across 8.7 years is not a tradable signal
frequency), and even that thin sample fails the Sharpe threshold. Crypto is
a categorical 0/48. The source's own backtest is on intraday futures with
true tick-level order-flow delta -- OBV's daily directional-volume proxy is
evidently too coarse and infrequent a signal to translate the edge to daily
equity/crypto bars.
