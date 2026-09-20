# Backtest Report: MACD Histogram Bullish Divergence Reversal

**Strategy file:** `strategies/2026-09-21_macd_histogram_divergence.py`
**Date:** 2026-09-21

## Hypothesis

Per a Google AI-overview synthesis of MACD-divergence trading guides (SGT
Markets, StockGro, Evest -- via browser_exec after `web_search`'s DDGS/Yahoo
backend hit repeated TLS RequestErrors on every query this iteration), a
MACD(12,26,9)-histogram bullish divergence occurs when price makes a lower
low over a lookback window while the histogram simultaneously makes a higher
low, confirmed by an upturn in the histogram itself. This is a new
technique/indicator combination for this repo (0 prior hits for "MACD
divergence" -- prior MACD entries use crossovers/zero-line crosses only).

## Grid test summary (Step 6)

Params swept: `lookback` in [10,20,30], `pct_tolerance` in [0.01,0.02],
`max_hold_days` in [15,30]; symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT
(crypto); `vol_regime_splits=3` (low/mid/high realized-vol terciles).
144 total grid cells.

```
pass_fraction: 0.083 (12/144)
by_asset_class: equity 2/72, crypto 10/72
by_vol_regime: low 12/48, mid 0/48, high 0/48
best_cell: crypto ETH/USDT, lookback=20/pct_tolerance=0.02/max_hold_days=15,
           low-vol tercile only, Sharpe=1.51
worst_cell: equity QQQ, mid-vol tercile, Sharpe=-1.08
```

Edge is entirely concentrated in the low-vol tercile; zero passing cells in
mid/high-vol regimes across all 96 non-low-vol cells. This is a strong signal
the "pass" cells are a narrow-regime artifact, not a robust full-cycle edge.

## Full-sample single-config validation (Step 7)

Initial grid-optimal config (`lookback=20, pct_tolerance=0.02,
max_hold_days=15`) on the FULL 2018-2026 sample (not just the low-vol
tercile):

| Symbol | Sharpe | Pass? | MDD | Pass? |
|---|---|---|---|---|
| BTC/USDT | 0.079 | FAIL | 0.546 | FAIL |
| ETH/USDT | 0.403 | FAIL | 0.540 | FAIL |
| QQQ | -0.176 | FAIL | 0.267 | FAIL |
| SPY | 0.333 | FAIL | 0.179 | PASS |

Broad local hand-search (lookback in [10,15,20,30,40] x pct_tolerance in
[0.005,0.01,0.02,0.03] x max_hold_days in [10,15,20,30,45], 100 combos per
symbol) for the best full-sample Sharpe achievable anywhere in this
neighborhood:

| Symbol | Best full-sample Sharpe | Config |
|---|---|---|
| BTC/USDT | 0.695 | lookback=10, pct=0.03, hold=20 |
| ETH/USDT | 0.900 | lookback=10, pct=0.01, hold=30 |
| QQQ | 0.584 | lookback=10, pct=0.03, hold=30 |
| SPY | 0.963 | lookback=15, pct=0.03, hold=10 (near-miss, best of the whole sweep) |

No symbol/config combination in this search clears the Sharpe>=1.0 threshold
on the full 2018-2026 sample. SPY comes closest at 0.963 but is still a
genuine miss, not a marginal near-miss worth chasing further (walk-forward
and TC-survival weren't even run given the headline Sharpe already fails).

## Decision (Step 8)

**REJECT** -- decisive. The grid's apparent 8.3% pass fraction is fully
explained by low-vol-regime overfitting; no config survives full-sample
validation on any of the 4 symbols. Diagnosis: the divergence-confirmation
logic (histogram ticking up while price makes a fresh low) fires too rarely
and/or too late to capture a tradable edge once blended across the full
volatility cycle -- consistent with several prior divergence-family
rejections in this KB (RSI/OBV divergence).
