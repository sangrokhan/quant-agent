# Ehlers Deviation-Scaled Oscillator (DSO) Zero-Line Cross + EMA Confluence

**Hypothesis:** John Ehlers' deviation-scaling technique normalizes an
oscillator's raw deviation-from-smoothed-price by its own recent RMS
dispersion, producing a bounded, volatility-adaptive momentum measure.
Per https://theindicatorlab.com/reviews/ehlers-deviation-scaled-oscillator/
(read via browser_exec), disclosed rule: "Enter long when Oscillator
crosses above zero (momentum shift), Histogram turns green and is rising,
Price is above a key moving average (e.g. 50 EMA) for confluence."
Operationalized as: DSO crosses above 0 while close > EMA(trend_window) ->
long; exit on DSO crossing back below 0, EMA trend break, or a
max_hold_days time-stop.

Source: https://theindicatorlab.com/reviews/ehlers-deviation-scaled-oscillator/
(via browser_exec fallback; web_search DDGS backend TLS/connection-error
failures on this iteration's initial queries).

## Step 6 Grid Test Summary (144 cells: 3 dso_window x 2 trend_window x 2
max_hold_days x 4 symbols x 3 vol regimes)

- pass_fraction: 0.229 (33/144)
- by_asset_class: equity 33/72 passed, crypto 0/72 passed (decisively
  rejected on crypto)
- by_vol_regime: low 18/48, mid 8/48, high 7/48 (edge concentrated in
  low-vol regime)
- best_cell: dso_window=14, trend_window=30, max_hold_days=15, SPY,
  low-vol regime, Sharpe=2.45
- worst_cell: dso_window=14, trend_window=50, max_hold_days=15, QQQ,
  high-vol regime, Sharpe=-1.07

## Step 7 Single-Config Validation (best config: dso_window=14,
trend_window=30, max_hold_days=15, full sample 2019-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward (4-split) | Param sensitivity (rel std) |
|--------|--------|-----|---------------------------|--------------------------|------------------------------|
| QQQ    | 0.667 (FAIL, thr 1.0) | 0.219 (PASS, thr 0.25) | 0.531 (PASS, thr 0.5) | 0.50 (FAIL, thr 0.75) | 0.121 (PASS, thr 0.5) |
| SPY    | 1.381 (PASS, thr 1.0) | 0.115 (PASS, thr 0.25) | 1.160 (PASS, thr 0.5) | 1.00 (PASS, thr 0.75) | 0.304 (PASS, thr 0.5) |

Walk-forward manual 4-equal-slice fallback used (vbt.utils.splitting.RangeSplitter
broken in this vectorbt install, per existing repo convention).

## Decision: REJECTED

QQQ fails Sharpe (0.667 < 1.0) and walk-forward (0.5 < 0.75 pass fraction,
only 2/4 splits positive) at the primary/grid-best config. SPY passes all
five validators individually, but the strategy is only validated per-symbol
(not jointly required to pass on both equities in this repo's convention),
and the grid shows the edge is narrow: crypto decisively rejected (0/72),
mid/high-vol regimes weak (8/48, 7/48 vs 18/48 low-vol). Not accepted as a
standalone strategy; SPY-only low-vol performance noted as a possible
narrower-scope revisit for a future iteration (e.g. SPY-specific config
with an explicit low-vol gate, similar to the accepted BB mean-reversion
QQQ vol-regime strategy's pattern).
