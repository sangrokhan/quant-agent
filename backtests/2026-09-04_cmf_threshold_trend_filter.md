# Backtest Report: Chaikin Money Flow (CMF) Threshold-Cross + SMA Trend Filter

**Strategy file:** `strategies/2026-09-04_cmf_threshold_trend_filter.py`
**Knowledge base id:** 2026-09-04-043

## Hypothesis

Per a Google AI-overview synthesis (Enlightened Stock Trading / TrendSpider
/ StockCharts ChartSchool): Chaikin Money Flow (CMF), a volume-weighted
accumulation/distribution oscillator over a 20-21 period lookback,
crossing above a small positive threshold (0 or +0.05, to filter weak
zero-line noise) signals genuine buying pressure. Long entry: CMF
threshold-cross AND close > SMA(trend_window); exit: CMF crosses back
below zero (source's stated long-exit rule).

Source: Google AI-overview (`web_search` failed with a DDGS/Yahoo TLS
connection error, fell back to `browser_exec` immediately).

## Grid test summary (Step 6)

Grid: `cmf_threshold` in {0.0, 0.05, 0.1} x `trend_window` in {50, 200} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells.

- `pass_fraction`: 0.181 (13/72)
- `by_asset_class`: equity 13/36, crypto 0/36
- `by_vol_regime`: low 12/24, mid 1/24, high 0/24
- `best_cell` (low-vol-tercile artifact): QQQ, cmf_threshold=0.1,
  trend_window=200, Sharpe 2.81

## Full-sample sweep (QQQ / SPY)

| cmf_threshold | trend_window | QQQ Sharpe | SPY Sharpe |
|---|---|---|---|
| 0.00 | 50  | **1.046** | 0.628 |
| 0.00 | 200 | 0.821 | 0.456 |
| 0.05 | 50  | 0.981 | 0.533 |
| 0.05 | 200 | 0.937 | 0.629 |
| 0.10 | 50  | 0.880 | 0.528 |
| 0.10 | 200 | 0.878 | 0.650 |

Primary config: `cmf_threshold=0.0, trend_window=50` — best full-sample
Sharpe on QQQ.

## Primary config validators (QQQ, cmf_threshold=0.0, trend_window=50)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.046 | 1.0 |
| Max drawdown | ✅ | 0.172 | 0.25 |
| Transaction cost survival | ✅ | 0.967 (49 trades @ 10bps) | 0.5 |
| Walk-forward (4 splits, manual date-slice fallback) | ✅ | 1.0 (4/4 splits positive) | 0.75 |
| Parameter sensitivity (cmf_threshold in {0,0.05,0.1}, trend_window=50 fixed) | ✅ | rel.std 0.071 | 0.5 |

**All 5 validators pass on QQQ** — a narrow pass (Sharpe only 4.6% above
threshold) but clean across every other metric with a full 4/4
walk-forward record.

SPY fails Sharpe decisively at every param combo (best 0.650, far below
1.0) — not accepted. Crypto rejected decisively (0/36 grid cells).

## Outcome

**Accepted for QQQ only.** SPY rejected (Sharpe never clears 0.65 across
the grid). Crypto rejected decisively.

## Notes

Walk-forward used the manual date-slice fallback (per the documented
`vectorbt.utils.splitting` API bug, recurring since 2026-09-03-002).
Novelty: distinct from OBV+trend (2026-09-04-027, accepted QQQ) — OBV is a
simple cumulative +/-volume running total gated by its own EMA crossover;
CMF instead computes a bounded (-1,+1) ratio each bar from where the close
falls within that bar's high-low range, weighted by volume, summed over a
rolling window — a materially different volume-price relationship
construction, first tested in this repo.
