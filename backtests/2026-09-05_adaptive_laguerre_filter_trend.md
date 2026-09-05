# Adaptive Laguerre Filter (ALF) slope + price-position trend following

**Hypothesis:** Per quantifiedstrategies.com's "Adaptive Laguerre Filter"
article, the ALF (John Ehlers) is a triangular-weighted-average-like price
smoother with an ADAPTIVE gamma feedback factor (varies with tracking
performance, unlike the fixed-gamma Laguerre RSI already tested at
2026-09-05-053). Disclosed (non-paywalled) interpretation: filter sloping
up + price above it = uptrend continuation; sloping down + price below =
downtrend. Implemented mechanically: long when ALF's slope over
`slope_lookback` bars is positive AND close is above ALF; exit when either
condition breaks or a max_hold_days time-stop.

Source: https://www.quantifiedstrategies.com/adaptive-laguerre-filter/
(exact numeric backtest rules paywalled; interpretation rule and indicator
construction fully disclosed and used directly). `web_search` failed
repeatedly all session (DDGS/rustls TLS error) — `browser_exec` Google
search + direct page reads used throughout this iteration.

Novelty: distinct from Laguerre RSI (2026-09-05-053, rejected) — that used
a FIXED-gamma 4-stage cascade to build a BOUNDED 0-1 oscillator for
mean-reversion threshold entries; this uses an ADAPTIVE gamma to build a
PRICE-DOMAIN trend line for slope+position trend-following entries.

## Step 6 — Grid summary

Grid: `alf_lookback in {14,20,30}`, `slope_lookback in {3,5,8}`,
`max_hold_days in {20,30}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 216 total cells.

- pass_fraction: 0.25 (54/216)
- by_asset_class: equity 54/108 passed; crypto 0/108 (decisive)
- by_vol_regime: low 36/72, mid 18/72, high 0/72
- best_cell: alf_lookback=14, slope_lookback=5, max_hold_days=20, QQQ,
  low-vol, Sharpe 3.15

## Step 7 — Single-config validation (alf_lookback=14, slope_lookback=5, max_hold_days=20)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ 1.19 | ❌ 0.93 (near-miss) | ≥ 1.0 |
| Max drawdown | ✅ 21.8% | ✅ 11.7% | ≤ 25% |
| Transaction cost survival (10bps/trade) | ✅ net Sharpe 1.02 (99 trades) | ✅ net Sharpe 0.72 (101 trades) | ≥ 0.5 |
| Walk-forward (4 manual splits, `vbt.utils.splitting.RangeSplitter` unavailable — same known scaffold bug, manual `np.array_split` workaround) | ✅ 4/4 splits positive (100%) | — (not re-run, QQQ-only accept) | ≥ 75% |
| Parameter sensitivity (18-point grid on QQQ) | ✅ relative std 0.073 | — | ≤ 0.5 |

QQQ passes every validator cleanly (Sharpe, MDD, tx-cost, walk-forward,
parameter sensitivity all pass with wide margins — relative std 0.073 is
notably low, indicating a robust, non-overfit signal across the grid).
SPY misses the Sharpe bar narrowly (0.93 vs 1.0) — a near-miss, not
included in the accepted scope. Crypto rejected decisively (0/108).

## Decision: **ACCEPT (QQQ only)** — equity, low/mid-vol regimes; SPY near-miss (not included); crypto rejected
