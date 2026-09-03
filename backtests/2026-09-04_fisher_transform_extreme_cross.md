# Backtest Report: Fisher Transform Extreme-Threshold-Gated Crossover

**Strategy file:** `strategies/2026-09-04_fisher_transform_extreme_cross.py`
**Knowledge base id:** 2026-09-04-051

## Hypothesis

Per a Google AI-overview synthesis (onetradejournal.com et al.): John
Ehlers' Fisher Transform normalizes price into a bounded (-1,+1) range,
then applies the inverse hyperbolic tangent transform to sharpen turning
points. Long entry: Fisher line drops below an extreme negative threshold
(-1.5) then crosses above its own 1-bar-lagged trigger line; exit on the
opposite crossover.

Source: Google AI-overview (`web_search` failed 5x with a DDGS/Yahoo TLS
connection error, fell back to `browser_exec` immediately per
loop-avoidance rule).

## Grid test summary (Step 6)

Grid: `window` in {8, 10, 14} x `extreme_threshold` in {1.0, 1.5} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells.

- `pass_fraction`: 0.111 (8/72)
- `by_asset_class`: equity 8/36, crypto 0/36
- `by_vol_regime`: low 0/24, mid 8/24, high 0/24 (unusual: the mid-vol
  tercile, not low-vol, is where this strategy's grid passes concentrate)
- `best_cell` (mid-vol-tercile artifact): QQQ, window=10,
  extreme_threshold=1.5, Sharpe 1.32

## Full-sample sweep (QQQ / SPY)

| window | extreme_threshold | QQQ Sharpe (trades) | SPY Sharpe (trades) |
|---|---|---|---|
| 8  | 1.0 | -0.500 (69) | -0.054 (64) |
| 8  | 1.5 | -0.245 (56) | -0.039 (43) |
| 10 | 1.0 | -0.179 (61) | -0.058 (59) |
| 10 | 1.5 | -0.222 (52) | -0.090 (45) |
| 14 | 1.0 | 0.038 (61)  | 0.287 (52)  |
| 14 | 1.5 | 0.050 (47)  | 0.267 (41)  |

All 12 (6 param combos x 2 symbols) full-sample results are near-zero to
negative — a decisive rejection, not a near-miss. Given the uniformly
weak/negative full-sample Sharpe, the remaining validator suite was
skipped per Step 7 minimum-subset guidance.

## Outcome

**Rejected** (decisive). Crypto rejected decisively (0/36 grid cells).

## Notes

First Fisher Transform (Ehlers DSP-derived normalization + inverse
hyperbolic tangent price transform, distinct from every prior oscillator
in this repo — RSI/CCI/Stochastic/Williams %R/UO all use raw price-range
ratios; Fisher Transform instead statistically normalizes price toward a
Gaussian distribution before transforming) strategy tested in this repo.
The extreme-threshold-gated crossover construction (require the Fisher
line to have recently touched -1.5 before trusting a bullish crossover)
produced results no better — and in most configs worse — than a pure
mean-reversion whipsaw, suggesting either the "recently extreme" lookback
window (5 bars) implemented here doesn't match the source's intended
gating logic, or the indicator's edge (if any) requires a shorter/faster
timeframe than this repo's daily bars (Fisher Transform is more commonly
used on intraday charts per multiple sources browsed this run).
