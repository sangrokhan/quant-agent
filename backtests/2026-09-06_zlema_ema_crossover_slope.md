# Zero-Lag EMA (ZLEMA) Fast/Slow Crossover + Slope Filter — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_zlema_ema_crossover_slope.py`
**Outcome:** REJECTED (QQQ near-miss on Sharpe; both fail transaction-cost survival)

## Hypothesis

John Ehlers' Zero-Lag EMA (Rocket Science for Traders, 2001) removes lag
via `ZLEMA = EMA(2*price - price.shift(lag))`. Per Google AI-overview
synthesis of TrendSpider/LuxAlgo/ArrowAlgo guides: long entry when a fast
ZLEMA crosses above a slower standard EMA while the ZLEMA's own slope is
rising; exit on reverse cross or slope turning negative. First ZLEMA
strategy tested in this repo.

Sources:
- `google_search:Zero Lag EMA crossover trading strategy entry exit rules`
- https://trendspider.com/learning-center/what-is-the-zero-lag-exponential-moving-average-zlema/ (ZLEMA history/mechanics)
- QuantifiedStrategies, LuxAlgo, and ArrowAlgo's dedicated ZLEMA-strategy pages all returned 404 at time of visit — relied on the AI-overview synthesis + TrendSpider mechanics page.

## Single-config validator results (best grid config: fast_span=8, slow_span=26, slope_window=3)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Param sensitivity (rel std) |
|---|---|---|---|---|
| QQQ | 0.988 (FAIL, thr 1.0, near-miss) | 0.173 (PASS) | 0.406 (FAIL, thr 0.5) | 0.112 (PASS) |
| SPY | 0.658 (FAIL) | 0.139 (PASS) | 0.072 (FAIL, thr 0.5) | 0.101 (PASS) |

Walk-forward: skipped (repo-wide pre-existing tooling bug, `vectorbt.utils.splitting` missing).

## Step 6 grid summary

- Grid: `param_grid={fast_span:[8,12,20], slow_span:[26,40], slope_window:[3]}`,
  `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
  2015-01-01 to 2026-09-01. 72 total cells.
- `pass_fraction`: 0.222 (16/72)
- `by_asset_class`: equity 16/36 (44%), crypto 0/36 (0%)
- `by_vol_regime`: low 10/24 (42%), mid 6/24 (25%), high 0/24 (0%) — fails entirely in high-vol
- `best_cell`: fast_span=8, slow_span=26, QQQ, mid-vol regime, Sharpe 1.885
- `worst_cell`: fast_span=12, slow_span=26, QQQ, high-vol, Sharpe -0.263

## Decision

**Rejected.** QQQ full-sample Sharpe (0.988) misses the 1.0 threshold by
a hair, and SPY misses more decisively (0.658). Both fail transaction-cost
survival badly (net Sharpe 0.406/0.072 vs 0.5 threshold) because the
crossover-with-slope-filter fires very frequently (406-428 trades over
~11.7 years, i.e. roughly one round-trip every 10 trading days) — the
extra slope confirmation filter did not meaningfully reduce whipsaw
trade count vs a plain EMA crossover. Max drawdown and parameter
sensitivity both pass comfortably (relative_std ~0.10-0.11, among the
most stable in this repo), so the underlying signal shape is not noise —
it's simply too cost-sensitive at realistic trading frequency. Crypto is
categorically unsuitable (0/36 cells) and high-vol regimes fail entirely
across both equities.

Worth a future revisit only with an explicit minimum-holding-period gate
(the same fix that rescued the Klinger Volume Oscillator near-miss,
2026-09-04-085) to cut trade count without changing the underlying
crossover logic — QQQ is close enough (0.988) that trimming costs alone
might clear the bar.
