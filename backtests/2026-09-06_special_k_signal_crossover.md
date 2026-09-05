# Backtest Report: Pring's Special K Signal-Line Crossover (2026-09-06)

**Strategy file:** `strategies/2026-09-06_special_k_signal_crossover.py`
**Knowledge base id:** 2026-09-06-107
**Outcome:** REJECTED (near-miss)

## Hypothesis

Pring's Special K (weighted sum of 12 SMA-smoothed rate-of-change legs
spanning 10 to 530-period lookbacks, capturing Pring's four-year business
cycle) crossing above its own 100-period-SMA signal line signals a long
entry; crossing back below exits; plus a `max_hold_days` time-stop.

## Sources

- Google AI-overview synthesis of Special K trading rules: "Buy or go long
  when the Special K line crosses above its signal line (typically a
  100-period simple moving average of the indicator)."
- https://chartschool.stockcharts.com/.../prings-special-k (StockCharts
  ChartSchool): confirms default 100-day SMA signal line, "Crossovers of
  the average typically signal a reversal in the direction of the primary
  trend"; also documents >=725 data points required for accurate
  computation.
- LuxAlgo/TradingView search-snippet formula for the full 12-leg weighted
  ROC/SMA combination used in `_special_k()`.

First Special-K strategy in this repo, distinct from the already-tested
simpler 4-leg KST (2026-09-04-057, 2026-09-06-100).

## Step 6 grid summary (signal_window in [50,100,150], max_hold_days in
[30,60], equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2016-01-01..2026-09-01)

- total_cells: 72, passed_cells: 15, **pass_fraction: 0.208**
- by_asset_class: equity 15/36 passed, crypto 0/36 passed
- by_vol_regime: low 10/24, mid 5/24, high 0/24
- best_cell: QQQ, signal_window=50, max_hold_days=60, low-vol regime, Sharpe 1.949
- worst_cell: SPY, signal_window=150, max_hold_days=30, high-vol regime, Sharpe -1.221

Meaningfully better than the prior iteration's MA Envelope grid (20.8% vs
3.7% pass fraction) and entirely confined to equity low/mid-vol regimes;
crypto rejected decisively (0/36).

## Step 7 single-config validation (QQQ, signal_window=50, max_hold_days=60,
full sample 2016-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.816 | >= 1.0 | FAIL |
| Max drawdown | 0.247 | <= 0.25 | PASS (borderline) |
| Transaction cost survival (10bps, 38 trades) | net Sharpe 0.772 | >= 0.5 | PASS |
| Walk-forward (4 splits) | pass_fraction 1.0 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (6-cell grid) | relative_std 0.302 | <= 0.5 | PASS |

SPY cross-check at the same config: full-sample Sharpe 0.788 (also fails);
signal_window=100 variant on SPY: Sharpe 0.558 (worse).

## Decision

**REJECTED (near-miss).** 4 of 5 validators pass cleanly (transaction-cost
survival, walk-forward — a perfect 4/4 split record, and parameter
sensitivity all look genuinely solid), but full-sample Sharpe on both QQQ
(0.816) and SPY (0.788) falls short of the 1.0 threshold. The grid's
standout Sharpe of 1.95 (QQQ, low-vol regime) does not hold up once tested
across the full multi-regime sample — consistent with a real but modest
edge that is not yet strong enough to accept outright. Worth revisiting: a
future iteration could try a shorter/adaptive signal line, an added trend
filter (e.g. SMA200 gate per the source's own "only trade in the direction
of the primary trend" guidance), or a tighter time-stop to see if Sharpe
can be pushed over 1.0 without breaking the currently-passing validators.
