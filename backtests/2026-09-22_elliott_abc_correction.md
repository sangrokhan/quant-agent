# 2026-09-22 — Elliott ABC Correction Entry (Wave C completion long)

**Hypothesis**: Source: https://algobars.com/strategy-templates/elliott/elliott-abc-correction/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). After a bullish impulse completes, price enters a corrective
ABC pullback: Wave A (initial pullback from peak), Wave B (counter-rally,
0.382-0.618 of A), Wave C (final decline, extends 0.618-1.272 of A). Long
entry at Wave C's completion with a bullish reversal candle, targeting a
new high beyond the pre-correction peak. Invalidation: C extending beyond
1.618x of A, or B retracing beyond the original peak. First Elliott
ABC-correction strategy in this repo (0 prior KB hits).

**Strategy file**: `strategies/2026-09-22_elliott_abc_correction.py`

**Grid test** (`run_grid_elliott_abc_correction.py`): param_grid =
`{pivot_window: [3, 5, 8], c_ext_max: [1.0, 1.272, 1.5]}` (c_ext_min fixed
at source default 0.618), symbols = equity(QQQ, SPY) + crypto(BTC/USDT,
ETH/USDT), vol_regime_splits=3.
- total_cells=108, passed_cells=9, pass_fraction=0.083
- by_asset_class: equity 8/54, crypto 1/54
- by_vol_regime: low 1/36, mid 3/36, high 5/36
- best_cell: SPY pivot_window=5/c_ext_max=1.5, high-vol, Sharpe 1.86
- SPY pivot_window=3/c_ext_max=1.5 passed 2/3 vol regimes -- best
  cross-regime consistency in the grid

**Manual per-symbol retune (SPY)**: a finer local search around the
promising SPY config found `pivot_window=5, c_ext_min=0.5, c_ext_max=1.5`
clears the full-sample Sharpe threshold:

| Metric | SPY (retuned) | QQQ (same config) | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.041 (pass) | 0.283 (FAIL) | ≥1.0 |
| Max drawdown | 0.110 (pass) | 0.125 (pass) | ≤0.25 |
| TX-cost survival | 0.975 (pass) | 0.232 (FAIL) | ≥0.5 |
| Walk-forward (4-split manual) | 1.0 (pass, all 4 splits Sharpe>0) | not run | ≥0.75 |
| Parameter sensitivity (across grid's pivot_window x c_ext_max combos, SPY) | **1.170 rel-std (FAIL)** | -- | ≤0.5 |

Crypto (BTC/USDT, ETH/USDT) at the same config decisively fails everything
(Sharpe near 0, MDD 0.47-0.77 -- likely also affected by
`data/loaders.py`'s known default-interval quirk when called without an
explicit `interval="1d"` kwarg, consistent with prior grid_test.py notes).

**Decision**: REJECTED. SPY passes Sharpe/MDD/TX-cost/walk-forward at the
manually retuned config, but **parameter sensitivity fails decisively**
(relative std 1.170, more than double the 0.5 threshold) across the
strategy's own coarse grid of pivot_window/c_ext_max combinations -- the
SPY pass is concentrated in a narrow, hand-tuned parameter neighborhood
rather than being robust to nearby parameter choices, a classic
curve-fitting signature. Per RESEARCH_LOOP.md Step 8, acceptance requires
ALL validators run for the primary config to pass; the parameter
sensitivity failure blocks acceptance despite the otherwise-clean SPY
metrics. QQQ and crypto fail decisively at the same config regardless.
