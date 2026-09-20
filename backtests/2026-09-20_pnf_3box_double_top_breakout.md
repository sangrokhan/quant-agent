# P&F 3-Box Double Top Breakout / Double Bottom Breakdown (QQQ)

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_pnf_3box_double_top_breakout.py`
**Source:** [stockcharts.com ChartSchool — P&F Price Objectives: Breakout and Reversal Method](https://chartschool.stockcharts.com/table-of-contents/chart-analysis/point-and-figure-charts/p-and-f-price-objectives/p-and-f-price-objectives-breakout-and-reversal-method) (visited via browser_exec fallback, web_extract returned a DDGS-backend "search-only" error); corroborating background from [tradealgo.com's P&F explainer](https://www.tradealgo.com/trading-guides/technical-analysis/point-and-figure-charts-the-classic-method-for-spotting-breakouts-and-price-targets).

## Hypothesis

Point & Figure charting filters sub-threshold noise by only recording a new
column when price reverses by a fixed "reversal amount" (standard: 3 boxes).
StockCharts describes the most basic, most frequent P&F signal as the
**Double Top Breakout** (current X-column's high exceeds the prior
X-column's high — a buy signal) and its mirror, the **Double Bottom
Breakdown** (current O-column's low breaches the prior O-column's low — a
sell signal). Operationalized as a long/flat overlay using percentage box
scaling (`box_size_pct`) and a `reversal_boxes` multiplier.

## Grid test summary (`grid_result_pnf_3box_double_top.json`)

- Grid: `box_size_pct` ∈ {0.01, 0.02, 0.03} × `reversal_boxes` ∈ {2, 3, 4} ×
  symbols {QQQ, SPY, BTC/USDT, ETH/USDT} × 3 vol-regime terciles = 108 cells.
- **pass_fraction: 0.25** (27/108)
- By asset class: equity 25/54 passed, crypto 2/54 passed — strategy is
  **equity-only**, decisively fails on crypto.
- By vol regime: low 20/36, mid 7/36, **high 0/36** — only works in
  low/mid realized-vol regimes; breaks down entirely in high-vol regimes.
- Best cell: QQQ, box_size_pct=0.01, reversal_boxes=2, low-vol, Sharpe=2.62.
- Worst cell: QQQ, box_size_pct=0.02, reversal_boxes=4, high-vol, Sharpe=-0.37.

## Single-config validation (QQQ, box_size_pct=0.01, reversal_boxes=2, full sample 2017-2026)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.098 | ≥1.0 |
| Max drawdown | ✅ | 0.210 | ≤0.25 |
| Transaction cost survival (10bps/trade, 79 trades) | ✅ | 1.014 net Sharpe | ≥0.5 |
| Walk-forward (4-split manual, vectorbt RangeSplitter API broken in installed version) | ✅ | 1.0 (4/4 splits positive Sharpe) | ≥0.75 |
| Parameter sensitivity (relative std across box_size_pct×reversal_boxes sweep) | ✅ | 0.046 | ≤0.5 |

All 5 validators pass on QQQ full-sample. **Accepted, equity-only scope**
(crypto and high-vol regimes explicitly excluded per grid findings above).

## Notes

- SPY at the same params (0.01/2) failed Sharpe (0.748); SPY's best
  combination was 0.01/3 (Sharpe 1.048, MDD 0.215, passed). QQQ and SPY
  need different `reversal_boxes` tuning — not a single universal config,
  consistent with the grid's low pass_fraction.
- Crypto (BTC/USDT, ETH/USDT) failed almost entirely (2/54) — the
  percentage-box-scaling P&F construction does not translate to crypto's
  higher baseline volatility without much wider boxes; not pursued further
  this iteration.
- First Point & Figure–derived strategy in this repo — distinct from
  Renko (fixed brick size, no reversal-amount rule) and from all
  Donchian/rolling-high-breakout strategies (raw daily high/low, no P&F
  noise-filtering column construction).
