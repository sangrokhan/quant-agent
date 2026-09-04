# Z-score Mean Reversion (Rolling Mean, Time-Stop Exit) — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_zscore_meanrev_timestop.py`
**Outcome:** REJECTED

## Hypothesis

Per https://changelly.com/blog/mean-revision-trading-crypto/'s crypto
mean-reversion guide, price deviations from a rolling moving-average mean
measured via z-score `(close - rolling_mean) / rolling_std` signal
reversion opportunities: z < -2 (oversold) is a long entry, exit when z
reverts back toward 0 (price reaches the mean), OR a 5-10 day time-based
exit if reversion doesn't occur. Distinct from BB mean-reversion
(-001/-002, band-based) and CCI/RSI mean-reversion variants already
tested — this uses a raw rolling-mean z-score directly rather than a
derived oscillator.

Source: https://changelly.com/blog/mean-revision-trading-crypto/ (found via
Google search fallback; `web_search` failed with a DDGS/Yahoo TLS
connection error on this query. Alpaca and CoinQuant candidate URLs from
the same search both 404'd on direct fetch.)

## Grid test summary (window x entry_z x max_hold_days, 2 equity + 2
crypto symbols, 3 vol regimes)

- total_cells: 216, passed_cells: 13, **pass_fraction: 0.060**
- by_asset_class: equity 13/108, crypto **0/108**
- by_vol_regime: low 6/72, mid 6/72, high 1/72
- best_cell: SPY, window=15/entry_z=2.5/max_hold_days=5, low-vol regime,
  Sharpe 1.59

## Full-sample Sharpe by config (equity only)

| config | QQQ | SPY |
|---|---|---|
| window=15, entry_z=2.5, hold=5  | -0.003 | 0.558 |
| window=15, entry_z=2.0, hold=5  | 0.785  | 0.343 |
| window=20, entry_z=2.0, hold=10 | 0.152  | 0.493 |
| window=15, entry_z=2.5, hold=10 | -0.037 | 0.468 |
| window=20, entry_z=2.5, hold=5  | 0.060  | 0.326 |

## Single-config validators (primary config: QQQ, window=15, entry_z=2.0,
max_hold_days=5 — best full-sample QQQ config found)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.785 | 1.0 |
| max_drawdown | pass | 0.120 | 0.25 |
| transaction_cost_survival | pass | 0.649 (net Sharpe after costs) | 0.5 |

82 round-trip trades over 7.7yr; cost drag only 0.082 (survives costs
easily), but the underlying Sharpe never crosses 1.0 in any tested
full-sample config on either symbol.

## Decision

**Rejected.** No config on either QQQ or SPY reaches the 1.0 Sharpe
threshold on the full sample (best: QQQ 0.785). Grid pass_fraction only
0.060 (13/216), concentrated in low/mid-vol regimes — consistent with the
source's own explicit warning that mean reversion breaks down in trending
markets and volatility spikes, and this repo's 2019-2026 sample was
predominantly trending. Crypto rejected decisively (0/108 grid cells).
Not implemented as a live strategy.
