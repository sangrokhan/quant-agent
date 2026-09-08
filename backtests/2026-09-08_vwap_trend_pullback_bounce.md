# VWAP Trend-Continuation Pullback Bounce — Backtest Report (REJECTED)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_vwap_trend_pullback_bounce.py`
**Knowledge base id:** 2026-09-08-128

## Hypothesis

Per https://forextester.com/blog/vwap/ ("Context: intraday uptrend. Price
rides above a rising Volume Weighted Average Price. Entry: wait for a clean
retrace to the VWAP line... Stop: a few ticks below the recent swing low or
below the lower VWAP band (-1σ)"), a pullback that touches a still-rising
rolling VWAP and closes back above it is a trend-continuation long entry
("buy support in an uptrend"), distinct from this repo's already-tested
VWAP-band mean-reversion (2026-09-04-052, decisively rejected) and Anchored
VWAP crossover variants (2026-09-04-138/2026-09-06-164).

## Grid test summary (validation/grid_test.py)

- Grid: `vwap_window` in {15,20,30} × `pullback_pct` in {0.003,0.005,0.01} ×
  `trend_lookback`=5, `max_hold_days`=15 (9 param combos) × symbols
  {QQQ, SPY, BTC/USDT, ETH/USDT} × 3 vol-regime terciles = 108 cells.
- **pass_fraction: 0.194** (21/108 cells)
- by_asset_class: equity 21/54 passed; **crypto 0/54 (decisive reject)**
- by_vol_regime: low 18/36; mid 3/36; **high 0/36**
- best_cell: SPY, vwap_window=30/pullback_pct=0.005, low-vol regime, Sharpe 2.25
- worst_cell: QQQ, vwap_window=30/pullback_pct=0.01, high-vol regime, Sharpe -0.79

Edge (where present) is concentrated almost entirely in the low-vol-regime
equity slice — high-vol regime and all of crypto show no edge.

## Single-config validators (best config: vwap_window=30, pullback_pct=0.005,
trend_lookback=5, max_hold_days=15)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full-sample) | 0.585 | 0.996 | ≥1.0 | **FAIL both** |
| Max drawdown | 0.186 | 0.089 | ≤0.25 | pass both |
| TC survival (net Sharpe, 10bps/trade) | 0.455 | 0.784 | ≥0.5 | QQQ fail, SPY pass |
| Walk-forward (4-quarter, manual fallback) | 0.75 | 1.0 | ≥0.75 | pass both |
| Parameter sensitivity (relative std, 9-combo grid) | 0.316 | 0.243 | ≤0.5 | pass both |

Num trades: QQQ 58, SPY 70 over 2019-01 to 2026-09.

## Decision: REJECTED

Full-sample Sharpe fails on both equities (QQQ 0.585 decisively, SPY 0.996
narrowly under the 1.0 threshold). The grid's low-vol-regime edge (Sharpe up
to 2.25) does not survive full-sample averaging across regimes — the same
pattern seen repeatedly in this knowledge base (a strategy that only works
in one narrow vol slice). Crypto rejected decisively (0/54 grid cells).

Worth a future revisit gated explicitly to the low-vol regime only (rather
than trading unconditionally across all regimes), similar to the accepted
2026-09-03-001 BB-meanrev-QQQ-volregime pattern — but that is a distinct
hypothesis/parameterization from what was tested this iteration.
