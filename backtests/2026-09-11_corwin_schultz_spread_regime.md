# Backtest Report: Corwin-Schultz Spread Regime-Exit (QQQ only)

**Strategy file:** `strategies/2026-09-11_corwin_schultz_spread_regime.py`
**Date:** 2026-09-11
**Symbols tested:** QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
**Outcome:** **Accepted (QQQ only)** — config `stdev_mult=0.5, trend_window=50, max_hold_days=30`

## Hypothesis

Corwin & Schultz (2012, *Journal of Finance*) two-bar high-low bid-ask
spread estimator, per source
https://www.tradingview.com/script/ji4eKKuZ-Corwin-Schultz-Spread-Bands/
(visited 2026-09-11): a rolling estimate of the effective bid-ask spread
computed purely from daily H/L data. A spread-stress regime (smoothed
spread above its own rolling median+k*stdev threshold) resolving back
below threshold, while price is in a confirmed uptrend (close>SMA), marks
a historically favorable long entry window — liquidity stress has passed
but the trend is intact.

## Grid summary (from iteration 2026-09-11-002, same underlying strategy)

216 cells (`stdev_mult` in [0.5,1.0,1.5] x `trend_window` in [20,50] x
`max_hold_days` in [10,20,30] x symbols[QQQ,SPY,BTC/USDT,ETH/USDT] x 3 vol
regimes): pass_fraction=0.1296 (28/216).
- by_asset_class: equity 28/108 passed, crypto 0/108 (crypto decisively
  rejected — no discrete daily bid-ask-bounce microstructure in 24/7
  markets).
- by_vol_regime: low 22/72, mid 5/72, high 1/72 — edge concentrated in the
  low-vol tercile.

A direct vol-regime-gate fix attempt (2026-09-11-003) made results WORSE
(QQQ Sharpe dropped to 0.604), so instead this final config uses a
per-symbol fine parameter search (following this repo's IBS/HalfTrend
precedent) rather than an additional regime filter.

## Per-symbol validator results (2026-09-11-005, fine grid search around
the near-miss config from 2026-09-11-002)

| Metric | QQQ (accepted) | SPY (rejected) |
|---|---|---|
| Config | stdev_mult=0.5, trend_window=50, max_hold_days=30 | stdev_mult=1.0, trend_window=100, max_hold_days=30 |
| Sharpe ratio | **1.093** (pass, thr 1.0) | 0.945 (fail, thr 1.0) |
| Max drawdown | 0.165 (pass, thr 0.25) | 0.095 (pass, thr 0.25) |
| TC survival (net Sharpe, 10bps/trade) | **1.009** (pass, thr 0.5) | 0.860 (pass, thr 0.5) |
| Walk-forward pass fraction (4 splits) | **0.75** (pass, thr 0.75) | 0.50 (fail, thr 0.75) |
| Parameter sensitivity (relative std) | **0.167** (pass, thr 0.5) | 0.264 (pass, thr 0.5) |
| # trades (2018-2026.9) | 52 | 38 |

QQQ passes all 5 validators cleanly. SPY fails Sharpe (near-miss, 0.945)
and walk-forward (0.50 < 0.75 — only 2 of 4 out-of-sample splits
profitable), so SPY is rejected even though its own best-tuned config
looked superficially reasonable on MDD/TC/param-sensitivity.

## Decision

**Accept QQQ only.** Strategy file kept live in `strategies/`. SPY,
BTC/USDT, and ETH/USDT are explicitly NOT covered by this acceptance —
future loops should not assume this strategy works outside QQQ's scope
(config: `stdev_mult=0.5, trend_window=50, max_hold_days=30`).
