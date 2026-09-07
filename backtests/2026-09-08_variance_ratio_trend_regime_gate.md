# Lo-MacKinlay Variance Ratio Trend-Regime Gate + EMA Crossover — QQQ/SPY/BTC/ETH

**Hypothesis:** Per Lo & MacKinlay (1988) and
https://twowaymind.com/article-variance-ratio's disclosed formula, the
Variance Ratio VR(k) = Var(k-period return) / (k * Var(1-period return))
formally tests the Random Walk Hypothesis; VR(k) > 1 signals positive
return autocorrelation ("trending/momentum... favorable for trend-
following algorithms and breakouts"), VR(k) < 1 signals negative
autocorrelation (mean-reverting, unfavorable for trend-following). Gates a
plain fast/slow EMA crossover to only trade the bullish crossover when
VR(k) >= vr_threshold (a statistically-trending regime). First Variance-
Ratio-based strategy in this repo (distinct from the already-tested
Hurst-exponent R/S-analysis regime gates, 2026-09-04-155/156).

Best config from grid search: `vr_threshold=1.0, fast_ema=10, slow_ema=50`
(vr_k=5, vr_window=60, max_hold_days=40 held fixed).

## Single-config validator results (best config)

| Validator | QQQ | SPY |
|---|---|---|
| sharpe_ratio | **FAIL** 0.443 (thr 1.0) | **FAIL** 0.391 (thr 1.0) |
| max_drawdown | pass 0.120 (thr 0.25) | pass 0.114 (thr 0.25) |
| transaction_cost_survival (10bps/trade, 32-37 trades) | **FAIL** 0.366 (thr 0.5) | **FAIL** 0.284 (thr 0.5) |

## Step 6 grid summary (param_grid: vr_threshold∈{1.0,1.1,1.2},
fast_ema∈{10,20}, slow_ema∈{30,50}; symbols QQQ/SPY (equity), BTC/USDT+
ETH/USDT (crypto); vol_regime_splits=3)

- **pass_fraction: 0.181** (26/144 cells)
- by_asset_class: equity 26/72 passed, **crypto 0/72 passed** (zero edge
  on crypto despite the underlying VR(k) regime-classification test being
  asset-agnostic in theory)
- by_vol_regime: low 22/48, mid 4/48, **high 0/48** -- edge concentrated
  almost entirely in low-vol regimes
- best_cell: SPY, low-vol regime, Sharpe 2.05
- worst_cell: SPY, high-vol regime, Sharpe -1.17

## Decision: REJECTED

Full-sample Sharpe fails on both QQQ and SPY at the best grid config
(0.443 / 0.391, both well below the 1.0 threshold), transaction-cost
survival also fails both, and crypto shows zero edge across the entire
72-cell crypto grid. The grid's individually-passing cells are
concentrated almost exclusively in low-vol regime slices, meaning the
apparent "best cell" Sharpe of 2.05 does not survive when averaged across
the full multi-regime sample -- consistent with regime-dependence rather
than a genuine standalone edge.

**Notes for future loops:** The VR(k) regime-classification itself may
still be informative even though this particular EMA-crossover
implementation didn't clear threshold -- a future variant could try (a) a
tighter vr_window or higher vr_k to sharpen the regime signal, or (b)
pairing the VR(k)>1 trending gate with a different trend-following entry
(e.g. Donchian breakout, already accepted on QQQ at 2026-09-04-054) rather
than a plain EMA crossover, since the crossover mechanism itself may be
diluting whatever edge the regime filter contributes.
