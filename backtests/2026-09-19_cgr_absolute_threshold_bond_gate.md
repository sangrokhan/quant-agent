# Copper/Gold Ratio (CGR) Absolute-Threshold Bond-Proxy Trend Gate — REJECTED

**Hypothesis:** Per Jay Kaeppel / SentimenTrader's "Copper/Gold Ratio
signals for metals, miners and bonds"
(https://sentimentrader.com/blog/coppergold-ratio-signals-for-metals-miners-and-bonds,
2022-08-08), the Copper/Gold Ratio (CGR = close(HG=F)*100 / close(GC=F),
scaled to the source's cents/lb-over-$/oz convention) crossing above a
disclosed fixed absolute level of 0.20 has historically preceded
above-average forward returns for LQD/HYG corporate bonds; below 0.19
preceded metals/miners strength instead. Adapted here as a standing
trend-confirmation gate for LQD/HYG themselves (long only while close >
SMA(trend_window) AND CGR >= cgr_threshold), rather than the source's
one-off event-study framing. Distinct from prior copper/gold-ratio variants
in this repo (2026-09-05-031/032 rolling z-score; 2026-09-10-039 ratio vs
its own trailing SMA) — this is the first to test the source's own
disclosed fixed absolute level directly.

**Data quirk found & fixed:** yfinance's `HG=F` returns copper in
dollars/lb, not the cents/lb COMEX convention the SentimenTrader piece's
0.19/0.20 thresholds are scaled to — raw `close(HG=F)/close(GC=F)` gives
~0.0017-0.0027, nowhere near 0.19-0.20. Multiplying copper close by 100
before dividing by gold close brings the series to the correct scale (mean
~0.192 over 2016-2026), matching the source's own historical CGR range.
Documented in the strategy file/code comment for future loops re-using
HG=F/GC=F.

## Step 6 — Grid test summary

Grid: `trend_window` in {50,100,150} x `cgr_threshold` in {0.18,0.20,0.22},
symbols equity={LQD,HYG} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3.
108 total cells.

- `pass_fraction`: 8/108 = **0.074**
- `by_asset_class`: equity 6/54 passed, crypto 2/54 passed
- `by_vol_regime`: low 7/36, mid 1/36, **high 0/36**
- `best_cell`: trend_window=150, cgr_threshold=0.18, LQD, low-vol regime,
  Sharpe=1.99
- `worst_cell`: trend_window=50, cgr_threshold=0.22, HYG, mid-vol regime,
  Sharpe=-1.70

The grid shows the strategy only works in a narrow low-vol-regime slice
(LQD specifically) — it does not hold up broadly across vol regimes or
asset classes.

## Step 7 — Single-config validation (best cell: LQD, trend_window=150,
cgr_threshold=0.18, full sample 2018-01 to 2026-09)

| Validator | Result | Value | Threshold | Pass |
|---|---|---|---|---|
| Sharpe ratio | full-sample | 0.031 | >= 1.0 | **FAIL** |
| Max drawdown | full-sample | 0.136 | <= 0.25 | pass |
| Tx-cost survival (5bps/trade, 86 trades) | net Sharpe | -0.139 | >= 0.5 | **FAIL** |
| Walk-forward (manual 4-split, `check_walk_forward` broken — see note) | pass_fraction | 0.5 | >= 0.75 | **FAIL** |
| Parameter sensitivity (9-cell trend_window x cgr_threshold sweep) | relative_std | 9.88 | <= 0.5 | **FAIL** |

`check_walk_forward` (validation/validators.py) raised
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` in
the installed vectorbt version — same pre-existing library issue already
noted in `backtests/2026-09-20_dxy_absolute_level_hysteresis_regime.md`.
Substituted a manual 4-way chronological split (qcut on row index): 2/4
splits had positive Sharpe.

Full-sample Sharpe (0.031) is drastically lower than the grid's best-cell
low-vol-regime Sharpe (1.99) — the edge found in Step 6's grid is entirely
a low-vol-regime artifact and does not survive full-sample testing, once
mid/high-vol regimes (where the gate performs poorly, 0/36 pass in
high-vol) are included. Parameter sensitivity is extremely unstable
(relative_std 9.88, nearly 20x the threshold) — small trend_window/
cgr_threshold perturbations flip the sign of full-sample Sharpe entirely,
confirming this is not a robust edge.

## Decision: REJECTED

4 of 5 validators fail decisively on the primary (best-grid-cell) config.
Only max-drawdown passes. The CGR-absolute-threshold construction does not
generalize beyond the narrow low-vol regime it was optimized on in the
grid search — a textbook overfitting/regime-selection artifact. Strategy
file kept in `strategies/` as a record of a rejected attempt (not live).
