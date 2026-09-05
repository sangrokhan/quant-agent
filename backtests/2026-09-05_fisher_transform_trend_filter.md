# Fisher Transform Crossover + 50-SMA Trend Filter — REJECTED

**Strategy file:** `strategies/2026-09-05_fisher_transform_trend_filter.py`
**Knowledge base id:** 2026-09-05-086
**Source:** https://enlightenedstocktrading.com/fisher-transform/

## Hypothesis

Ehlers Fisher Transform crossover (long when Fisher crosses above its
signal line from below -1.5), gated by requiring price above its
50-period SMA, would fix the previously-rejected ungated Fisher Transform
strategy (2026-09-04-051, full-sample Sharpe -0.500 to 0.287 across 12
cells).

## Grid test summary (96 cells: equity QQQ/SPY + crypto BTC/ETH, params
entry_threshold in {-1.5,-1.2} x trend_window in {50,100} x
max_hold_days in {15,20}, vol_regime_splits=3)

- pass_fraction: 0.125 (12/96)
- by_asset_class: equity 12/48, crypto 0/48
- by_vol_regime: low 12/32, mid 0/32, high 0/32
- Naive best_cell (low-vol tercile): QQQ, entry_threshold=-1.2,
  trend_window=50, max_hold_days=15, Sharpe 1.948 — but this is a
  narrow-slice artifact.

## Full-sample re-check (best params per symbol)

| Symbol | Best params | Full-sample Sharpe | Threshold |
|---|---|---|---|
| QQQ | entry=-1.2, trend=50, hold=15 | 0.445 | 1.0 (FAIL) |
| SPY | entry=-1.5, trend=100, hold=15 | 0.468 | 1.0 (FAIL) |
| BTC/USDT | entry=-1.5, trend=100, hold=15 | 0.036 | 1.0 (FAIL) |
| ETH/USDT | entry=-1.2, trend=50, hold=15 | 0.107 | 1.0 (FAIL) |

## Validators (QQQ, entry=-1.2/trend=50/hold=15)

- Sharpe ratio: FAIL (0.445 < 1.0)
- Max drawdown: not gating (Sharpe already decisive fail)
- Walk-forward / txcost / param sensitivity: skipped — Sharpe fail is
  decisive across all symbols and all grid combos, no near-miss worth
  the additional validator budget.

## Verdict: REJECTED

The 50-SMA trend filter reduces whipsaws but the underlying Fisher
Transform crossover signal itself lacks sufficient edge on this asset
universe/timeframe. Grid's nominal best_cell is a low-vol-tercile
artifact that does not hold on full-sample re-check — consistent with
this repo's repeated finding (see 2026-09-04-040 Vortex note) that
grid pass_fraction/best_cell alone is insufficient without a full-sample
config re-check.
