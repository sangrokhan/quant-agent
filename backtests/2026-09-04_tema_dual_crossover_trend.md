# Backtest Report: TEMA Dual Crossover with 200-SMA Trend Filter

**Strategy file:** `strategies/2026-09-04_tema_dual_crossover_trend.py`
**Knowledge base id:** 2026-09-04-068

## Hypothesis

Per Google AI-overview (PyQuantLab/GoCharting synthesis): TEMA (Triple
Exponential Moving Average) = 3*EMA1 - 3*EMA2 + EMA3, distinct
construction from ZLEMA/HMA/KAMA already tested. Long entry: fast TEMA(9)
crosses above slow TEMA(21) AND close > SMA(200); exit on stop-and-reverse
(fast crosses back below slow) OR trend invalidation (close < SMA(200)).

Source: Google AI-overview synthesis (web_search failed with a
DDGS/Yahoo TLS connection error, fell back to browser_exec).

## Grid test summary

- Grid: `fast_window` in {9,12} x `slow_window` in {21,30} x symbols
  {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol-regime terciles = 48 cells.
- pass_fraction: 0.1875 (9/48)
- by_asset_class: equity 9/24, crypto 0/24
- by_vol_regime: low 5/16, mid 4/16, high 0/16
- best_cell: QQQ, fast=9/slow=21, mid-vol tercile, Sharpe 1.59
- worst_cell: QQQ, fast=12/slow=21, high-vol tercile, Sharpe -0.41

## Full-sample sweep (4 fast/slow combos)

| Symbol | 9/21 | 12/21 | 9/30 | 12/30 |
|---|---|---|---|---|
| QQQ | **0.848** | 0.642 | 0.666 | 0.661 |
| SPY | 0.459 | 0.420 | 0.563 | 0.154 |

Primary config selected: `fast_window=9, slow_window=21` (source's
default parameters; also best full-sample on QQQ).

## Single-config validator suite (primary config, fast=9/slow=21)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | 0.848 (fail, thr 1.0) | 0.459 (fail, thr 1.0) |
| Max drawdown | 0.198 (pass, thr 0.25) | 0.105 (pass) |
| TC survival | 0.714 (pass, thr 0.5) | 0.273 (fail, thr 0.5) |
| Walk-forward | 2/4 splits positive (**fail**, thr 0.75) | 3/4 splits positive (pass) |
| Parameter sensitivity | rel.std 0.119 (pass) | rel.std 0.378 (pass) |

## Outcome

**Rejected.** QQQ is a near-miss on Sharpe (0.848, 15% shortfall) but also
fails walk-forward decisively (only 2/4 splits positive). SPY fails
Sharpe (0.459) and TC-survival (0.273) more decisively. Crypto rejected
decisively (0/24 grid cells).

## Notes

Novelty: first TEMA (recursive triple-EMA with lag-cancelling weights)
crossover strategy in this repo, distinct from ZLEMA -066 (de-lag via
price extrapolation), HMA -026 (nested WMAs), KAMA -048 (Efficiency-Ratio
adaptive). Trend-filter-gated fast crossover (9/21, close to the near-
miss ZLEMA family) still doesn't clear the bar on this sample — the
combination of a fast 9-period signal with a 200-SMA trend gate produces
67-70 trades over 7.7yr, moderate turnover that isn't the primary driver
of failure here (TC-survival actually passes on QQQ); the core signal
itself (Sharpe <0.85 on both symbols) appears to lack sufficient edge.
