# Z-Score Range Box Breakout — Backtest Report (2026-09-21)

## Hypothesis

Per TheIndicatorLab's review of "Z_Score_Range_Boxes_Breakout"
(https://theindicatorlab.com/reviews/z-score-range-boxes-breakout/, read via
browser_exec this iteration — web_search backend was intermittently failing
so the browser fallback was used for discovery): a rolling z-score of close
vs. its own rolling mean/std forms a compression "box" during periods where
|z| stays inside a tight deadband for several consecutive bars; a breakout
signal fires only when price closes outside that box's high AND the
breakout bar's own z-score exceeds a statistical significance threshold
(disclosed range 1.5–2.0). This differs from a plain Donchian breakout
(many prior rejected variants in this repo) by requiring the box to have
first formed during genuine low-volatility compression, and by requiring
the breakout itself to be a statistical outlier rather than a bare price
cross.

Source URL: https://theindicatorlab.com/reviews/z-score-range-boxes-breakout/

## Strategy file

`strategies/2026-09-21_zscore_range_box_breakout.py`

## Grid test summary (Step 6)

- Grid: `box_window` ∈ {20, 30, 45}, `z_threshold` ∈ {1.5, 1.75, 2.0}
- Symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- Vol regime splits: 3 (low/mid/high terciles)
- Total cells: 108, passed: 41, **pass_fraction = 0.380**
- By asset class: equity 18/54 passed, crypto 23/54 passed
- By vol regime: low 31/36 passed, mid 7/36 passed, high 3/36 passed
  (strategy works almost exclusively in low-vol regimes, as expected from
  the compression-box mechanism, but degrades sharply outside it)
- Best cell: box_window=30, z_threshold=1.75, QQQ, low-vol, Sharpe=2.53
- Worst cell: box_window=45, z_threshold=2.0, SPY, high-vol, Sharpe=-1.47
- Chosen best-config for single-config validation: box_window=45,
  z_threshold=1.75 (QQQ) — best average across regimes among param combos
  with balanced equity+crypto coverage.

## Single-config validation (Step 7) — QQQ, box_window=45, z_threshold=1.75, full sample 2018-01-01..2026-09-01

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.633 | ≥1.0 |
| Max drawdown | pass | 0.142 | ≤0.25 |
| Transaction cost survival | pass | net Sharpe 0.549 (49 trades, 10bps/trade) | ≥0.5 |
| Walk-forward (4 splits) | pass | 1.0 pass fraction (manual fallback split, vbt splitting API unavailable) | ≥0.75 |
| Parameter sensitivity | pass | relative std 0.271 (grid of 9 box_window×z_threshold combos, QQQ low-vol) | ≤0.5 |

## Decision: REJECTED

Full-sample Sharpe (0.633) falls well short of the 1.0 threshold, even
though the grid showed strong performance specifically within low-vol
regime slices (best cell Sharpe 2.53). The strategy is regime-dependent in
a way that drags the full-period, regime-unconditional Sharpe down —
consistent with the grid's own low/mid/high pass-rate breakdown (31/36,
7/36, 3/36). All other validators pass, so this is a near-miss on Sharpe
alone; a future iteration could revisit by explicitly gating entries to a
detected low-vol regime (analogous to the accepted
`2026-09-03_bb_meanrev_qqq_volregime.py` pattern) rather than trading the
box-breakout signal unconditionally across all vol regimes.
