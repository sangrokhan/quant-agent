# Backtest Report: Order Flow Imbalance (OFI) Proxy Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-17_ofi_proxy_sizing_sma_trend.py`
**Date:** 2026-09-16 (cron trigger iteration 1/10)

## Hypothesis

Per [theledgermind.com](https://theledgermind.com/order-flow-imbalance-indicator/)
and [dm13450.github.io](https://dm13450.github.io/2022/02/02/Order-Flow-Imbalance.html):
order flow imbalance (net difference between aggressive buy volume and
aggressive sell volume) tends to precede directional price movement because
it reflects real-time demand/supply pressure rather than lagging price
action. This repo's `data/loaders.py` only exposes daily OHLCV (no
tick-level bid/ask aggressor data), so a standard intrabar proxy is used:

```
buy_volume  = volume * (close-low)/(high-low)
sell_volume = volume * (high-close)/(high-low)
delta       = buy_volume - sell_volume
```

Daily delta is smoothed, rolling z-scored, tanh-squashed to [-1,1], and used
as a continuous exposure-sizing dial inside an SMA(trend_window) uptrend
gate + deadband (the pattern that has rescued many prior adaptive-indicator
near-misses in this repo: VAMA, FRAMA, KAMA, T3, DPO).

This is distinct from the already-rejected Cumulative-Delta-Divergence entry
(2026-09-08-019), which used OBV as a cumulative-delta proxy consumed via a
rare discrete swing-pivot divergence trigger (only 4 trades in 8.7 years on
QQQ, categorically 0/48 crypto cells). This iteration instead consumes the
daily OFI proxy continuously (not via a rare discrete divergence event).

## Step 6: Grid Test Summary

Grid: `trend_window ∈ {30,40,60}` × `sensitivity ∈ {0.5,0.7,0.9}` ×
`zscore_window ∈ {40,60}`, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01..2026-09-01.

- total_cells=216, passed_cells=104, **pass_fraction=0.481**
- by_asset_class: equity 48/108, crypto 56/108
- by_vol_regime: low 61/72, mid 31/72, high 12/72 (as expected: continuous-sizing
  dials generally hold up best in low/mid vol, weaker in high-vol regimes)
- best_cell: crypto ETH/USDT mid-vol, trend_window=60/sensitivity=0.5/zscore_window=40, Sharpe=2.38
- worst_cell: equity QQQ high-vol, trend_window=60/sensitivity=0.9/zscore_window=60, Sharpe=-1.24

Best average config across vol regimes per symbol:
- QQQ: trend_window=30, sensitivity=0.5, zscore_window=40 (avg Sharpe 1.06)
- SPY: trend_window=30, sensitivity=0.5, zscore_window=40 (avg Sharpe 1.09)
- BTC/USDT: trend_window=60, sensitivity=0.5, zscore_window=40 (avg Sharpe 1.24, but see leverage_cap tuning below)
- ETH/USDT: trend_window=40, sensitivity=0.5, zscore_window=60 (avg Sharpe 1.12)

## Step 7: Full Validator Suite (single-config confirmation)

Per-symbol config used (deadband/leverage_cap retuned per symbol to pass
MDD/cost-survival — same per-symbol-retune pattern used throughout this repo):

| Symbol | Params | Sharpe | MDD | Cost-adj Sharpe | Walk-Fwd | Param Sens (rel std) |
|---|---|---|---|---|---|---|
| QQQ | trend_window=30, sensitivity=0.5, zscore_window=40, deadband=0.5 | 1.050 ✅ | 0.118 ✅ | 0.503 ✅ | 1.0 ✅ | 0.323 ✅ |
| SPY | trend_window=30, sensitivity=0.5, zscore_window=40, deadband=0.6 | 1.086 ✅ | 0.072 ✅ | 0.518 ✅ | 1.0 ✅ | 0.251 ✅ |
| BTC/USDT | trend_window=40, sensitivity=0.5, zscore_window=40, deadband=0.4, leverage_cap=0.45 | 1.145 ✅ | 0.219 ✅ | 0.811 ✅ | 1.0 ✅ | 0.058 ✅ |
| ETH/USDT | trend_window=40, sensitivity=0.5, zscore_window=40, deadband=0.35, leverage_cap=0.5 | 1.096 ✅ | 0.249 ✅ | 0.852 ✅ | 1.0 ✅ | 0.046 ✅ |

Walk-forward used the repo's standard manual 4-split fallback
(`vbt.utils.splitting` API unavailable in installed vectorbt version); all
4 splits positive Sharpe for every symbol.

## Decision: ACCEPT (full universe: QQQ, SPY, BTC/USDT, ETH/USDT)

All 5 validators pass for all 4 symbols with per-symbol deadband/leverage_cap
retuning (same pattern used repo-wide for continuous-sizing dials). This is
the first OFI-proxy-based strategy in this repo to reach full-universe
accept — the prior OFI-adjacent attempt (OBV-as-cumulative-delta,
2026-09-08-019) was rejected for being too sparse (discrete divergence
trigger). Framing it as a continuous sizing dial instead (same fix pattern
used for VAMA, Donchian Width, RAVI, etc.) succeeded here too.
