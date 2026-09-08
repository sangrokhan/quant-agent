# Cumulative RSI(2) Mean Reversion — Backtest Report (ACCEPTED, SPY only)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_cumulative_rsi2_meanrev.py`
**Knowledge base id:** 2026-09-08-134

## Hypothesis

Per https://www.quantitativo.com/p/squeezing-more-profits-with-cumulative,
Larry Connors' Cumulative RSI concept: sum the past `cum_days` daily
readings of a 2-period RSI into one "Cumulative RSI" value; buy when it's
below `entry_threshold`; exit when the single-day RSI(2) closes above
`exit_threshold`; gated by a 200-day SMA uptrend filter. Distinct from
every other RSI(2)-family strategy in this repo (plain single-day RSI(2)
threshold 2026-09-03-005, multi-day monotonic-decline R3 variants, N-
consecutive-days-persistence 2026-09-08-089) via its SUMMED-magnitude
construction, capturing both how oversold and for how long in one number.

## Grid test summary (validation/grid_test.py)

- Grid: `cum_days`=2 × `entry_threshold` in {30,35,40} × `exit_threshold`
  in {55,60} × `trend_window`=200 (6 combos) × {QQQ, SPY, BTC/USDT,
  ETH/USDT} × 3 vol-regime terciles = 72 cells.
- **pass_fraction: 0.292** (21/72)
- by_asset_class: equity 21/36; **crypto 0/36 (decisive reject)**
- by_vol_regime: low 12/24; mid 6/24; high 3/24
- best_cell: SPY, entry_threshold=40/exit_threshold=60, low-vol regime,
  Sharpe 1.938

## Single-config validators (config: cum_days=2, entry_threshold=35,
exit_threshold=60, trend_window=200)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full-sample) | 0.926 | 1.051 | ≥1.0 | QQQ near-miss FAIL, SPY pass |
| Max drawdown | 0.098 | 0.077 | ≤0.25 | pass both |
| TC survival (net Sharpe, 10bps/trade) | 0.777 | 0.811 | ≥0.5 | pass both |
| Walk-forward (4-quarter, manual fallback) | 0.75 | 0.75 | ≥0.75 | pass both (1st quarter failed both) |
| Parameter sensitivity (relative std, 6-combo grid) | 0.062 | 0.154 | ≤0.5 | pass both |

Num trades: QQQ 59, SPY 61 over 2019-01 to 2026-09.

## Decision: ACCEPTED (SPY only); QQQ near-miss; crypto rejected decisively

SPY passes all five validators. QQQ narrowly misses the Sharpe threshold
(0.926) while passing every other validator — a genuine near-miss worth a
future revisit (e.g. QQQ-specific parameter re-tune). Crypto (BTC/USDT,
ETH/USDT) shows 0/36 grid-cell passes. Kept live in `strategies/` scoped to
SPY only, matching this repo's convention for single-symbol accepts.
