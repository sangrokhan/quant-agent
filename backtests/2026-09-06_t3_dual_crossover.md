# Backtest Report: T3 (Tillson) Dual Moving-Average Crossover (2026-09-06)

**Strategy file:** `strategies/2026-09-06_t3_dual_crossover.py`
**Knowledge base id:** 2026-09-06-108
**Outcome:** REJECTED

## Hypothesis

Tillson T3 (sextuple-cascaded-EMA polynomial recombination, volume_factor
b=0.7) dual moving-average crossover: fast-period T3 crossing above
slow-period T3 (Golden Cross) signals a long entry; crossing back below
(Death Cross) exits; plus a `max_hold_days` time-stop.

## Sources

- WH SelfInvest "The Tillson T3 Moving Average and Histogram" (search
  snippet): "When the fast T3 crosses the slow T3 upwards, the trend is
  positive. This is a buy signal."
- TradingView "Tillson T3 Moving Average MTF" description: fast T3 crossing
  slower T3 from below = Golden Cross = bullish entry signal.

Distinct from this repo's already-tested single-line T3/Coral variants
(2026-09-04-131 slope-flip, 2026-09-05-090 price-crosses-T3) — this is a
genuine dual-line (fast T3 vs slow T3) crossover.

## Step 6 grid summary (fast_period in [5,10,15], slow_period in
[30,50,100], equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01..2026-09-01)

- total_cells: 108, passed_cells: 18, **pass_fraction: 0.167**
- by_asset_class: equity 18/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 0/36, high 0/36
- best_cell: QQQ, fast_period=5, slow_period=100, low-vol regime, Sharpe 2.591
- worst_cell: QQQ, fast_period=10, slow_period=100, high-vol regime, Sharpe -1.450

Entirely confined to low-vol equity cells; zero passes in mid/high-vol
regimes and crypto entirely.

## Step 7 single-config validation (QQQ, fast_period=5, slow_period=100,
full sample 2018-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.486 | >= 1.0 | FAIL |
| Max drawdown | 0.175 | <= 0.25 | PASS |
| Transaction cost survival (10bps, 14 trades) | net Sharpe 0.456 | >= 0.5 | FAIL |
| Walk-forward (4 splits) | pass_fraction 1.0 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (9-cell grid) | relative_std 0.223 | <= 0.5 | PASS |

## Decision

**REJECTED.** Fails 2 of 5 validators (Sharpe 0.486, well below threshold;
net-of-cost Sharpe 0.456 also below 0.5). The grid's best cell (Sharpe 2.59)
was a low-vol-regime fluke that does not generalize to the full sample —
similar failure mode to this iteration cycle's prior two rejections (MA
Envelope, Special K). Parameter sensitivity and walk-forward both look
solid, so the signal itself is directionally stable, just too weak/low
frequency (only 14 trades over the full 2018-2026 window) to clear the
Sharpe bar even before costs.
