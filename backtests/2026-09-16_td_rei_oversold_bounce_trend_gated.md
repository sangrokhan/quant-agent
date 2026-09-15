# Backtest Report: TD REI (DeMark Range Expansion Index) oversold-bounce, trend-gated

**Strategy file:** `strategies/2026-09-16_td_rei_oversold_bounce_trend_gated.py`
**Date:** 2026-09-16

## Hypothesis

Thomas DeMark's Range Expansion Index (TD REI, 1994): arithmetically-
calculated momentum oscillator comparing current-bar high/low displacement
against 5/6-bar-ago and 2-vs-7/8-bar-ago reference points, normalized by
sum of absolute displacements over a lookback window N. Exact formula per
https://www.linnsoft.com/techind/demark-range-expansion-index:

```
condition = (HI>=LO[5] OR HI>=LO[6]) AND (LO<=HI[5] OR LO<=HI[6])
         OR (HI[2]>=CL[7] OR HI[2]>=CL[8]) AND (LO[2]<=CL[7] OR LO[2]<=CL[8])
VALUE = HI-HI[2]+LO-LO[2] if condition else 0
ABSVALUE = |HI-HI[2]|+|LO-LO[2]| if condition else 0
TD_REI = 100 * SUM(VALUE,N) / SUM(ABSVALUE,N)
```

Long entry: REI crossed below oversold_threshold (default -60) within the
last `lookback_confirm` bars and has now turned up, gated by close above
SMA(trend_window). Exit on REI>exit_threshold, trend break, or time-stop.
First REI strategy in this repo — distinct from every other oscillator
threshold-cross already tested via its unique true-high/low-displacement
construction.

Sources:
- https://www.quantifiedstrategies.com/range-expansion-index/ (interpretation,
  overbought/oversold conventions, DeMark's own QQQ example noting 49% MDD
  with no trend filter — flagged as a risk warning, addressed here by adding
  a trend gate)
- https://www.linnsoft.com/techind/demark-range-expansion-index (exact
  disclosed RTL formula, primary implementation source)

## Grid test (Step 6)

Grid: `rei_period`∈{5,8,13} × `oversold_threshold`∈{-45,-60} ×
`trend_window`∈{50,100,150}, symbols {QQQ, SPY} × {BTC/USDT, ETH/USDT},
vol_regime_splits=3. 216 cells total.

- **pass_fraction: 0.213** (46/216)
- by_asset_class: equity 28/108 (0.259), crypto 18/108 (0.167)
- by_vol_regime: low 30/72 (0.417), mid 9/72 (0.125), high 7/72 (0.097)
- best_cell: QQQ, rei_period=5/oversold=-60/trend_window=50, low-vol, Sharpe 2.63

## Full-sample validators (Step 7), 2019-01-01 to 2026-09-01

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass frac | Param sensitivity (rel std) | All 5 pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.359 (pass) | 0.111 (pass) | 0.882 (pass) | 1.00 (pass) | 0.622 (**FAIL**, thr 0.5) | **No** |
| SPY | 0.858 (**FAIL**, thr 1.0) | 0.103 (pass) | 0.251 (**FAIL**, thr 0.5, decisive) | 1.00 (pass) | 0.468 (pass) | **No** |
| BTC/USDT | 0.611 (**FAIL**, decisive) | 0.330 (**FAIL**) | 0.527 (pass) | 0.75 (pass) | 0.265 (pass) | **No** |
| ETH/USDT | 1.036 (pass) | 0.253 (**FAIL**, near-miss) | 0.977 (pass) | 1.00 (pass) | 0.447 (pass) | **No** |

A dedicated finer sweep of QQQ's `rei_period`/`oversold_threshold`/
`trend_window` (3×3×3=27 additional configs) found no combination clearing
both Sharpe/MDD AND parameter-sensitivity simultaneously — QQQ's headline
metrics look strong at one specific config but the signal is not robust to
small parameter perturbations (a genuine overfitting flag, not a fixable
near-miss).

## Decision (Step 8)

**Reject: all 4 symbols.** QQQ fails parameter-sensitivity decisively
(0.622 vs 0.5, and a follow-up 27-combo sweep found no rescue). SPY fails
both raw Sharpe and transaction-cost-survival decisively (high trade
frequency at 172 trades erodes the edge). BTC/USDT fails Sharpe and MDD
both decisively. ETH/USDT passes 4/5 but MDD near-misses (0.253 vs 0.25).
Consistent with DeMark's own disclosed example (49% MDD on QQQ without a
trend filter) — even with a trend gate added, this indicator's edge does
not clear this repo's validator bar broadly. Not pursued further this
iteration.
