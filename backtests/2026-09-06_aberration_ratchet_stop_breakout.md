# Aberration (Fitschen 1986) Ratchet-Stop Breakout, Long-Only

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_aberration_ratchet_stop_breakout.py`
**Knowledge base id:** 2026-09-06-144

## Hypothesis

Per Concretum Research's Substack article "How to Size Your Trend Trades"
(https://concretumgroup.substack.com/p/how-to-size-your-trend-trades): the
Aberration strategy (Keith Fitschen, 1986) is a Bollinger-Band-based
trend-following framework: entry on a breakout above the upper band
(SMA(50) + 2*STD), exit when price crosses back below the SMA -- but with
the source's own explicit modification, "a monotonic adjustment of the
moving-average-based stop... permitted to move only upward" (for longs),
acting as a ratcheting trailing-stop constraint distinct from a plain
non-monotonic SMA-cross exit. First Aberration-family strategy in this repo
(distinct from all prior standard Bollinger Band mean-reversion/breakout
variants, which did not use a ratcheted stop line).

## Grid test (Step 6)

324 cells: `sma_window` in [30,50,70] x `std_mult` in [1.5,2.0,2.5] x
`max_hold_days` in [40,60,90] x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol
terciles.

- **Overall pass_fraction:** 0.179 (58/324)
- **by_asset_class:** equity 58/162 (0.358); crypto 0/162 (decisive reject)
- **by_vol_regime:** low 44/108 (0.407); mid 14/108 (0.130); high 0/108
  (decisive reject in high-vol)
- **Best cell:** sma_window=50/std_mult=1.5/max_hold_days=90, QQQ,
  low-vol regime, Sharpe=2.98

## Single-config validators (best-cell config, QQQ full sample, 24 trades)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.927 | 1.0 | **FAIL (near-miss)** |
| Max drawdown | 0.256 | 0.25 | **FAIL (near-miss)** |
| Transaction cost survival | 0.896 | 0.5 | pass |
| Walk-forward (manual 4-fold split) | 0.75 (3/4 folds Sharpe>0) | 0.75 | pass (barely) |
| Parameter sensitivity (relative std across sma_window x std_mult @ max_hold=90) | 0.603 | 0.5 | **FAIL** |

## Decision: REJECTED

Two near-misses (Sharpe 0.927 just under 1.0, MDD 0.256 just over 0.25) plus
a decisive parameter-sensitivity failure (0.603 relative std, above the 0.5
threshold) indicate the strategy's edge is real but too fragile/inconsistent
across nearby parameter choices to accept as-is. Crypto and high-vol regimes
are decisively rejected across the whole grid (0 passes). Equity/low-vol is
the only pocket showing promise (0.407 pass fraction) but doesn't survive
full-sample confirmation cleanly. A future loop could revisit with a
regime-gated variant (e.g. only trade when realized vol is below its own
trailing median) given the stark low-vol-only pattern, similar to prior
"regime-gated revisit" candidates flagged elsewhere in this repo.
