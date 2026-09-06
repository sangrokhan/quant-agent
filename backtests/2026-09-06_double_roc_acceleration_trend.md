# Backtest Report: Double ROC (Acceleration) Trend Continuation (2026-09-06)

**Hypothesis:** Per Ocean_Drive's "Double ROC (Acceleration)" TradingView
indicator guide (source's own reading rule: "A cross above the zero line
indicates that upward momentum is accelerating"): a second-derivative
momentum measure (Outer ROC = ta.change of the Inner ROC, avoiding
divide-by-zero distortion from naively taking %change of an
already-zero-crossing oscillator) crossing from negative to positive,
while price is above its trend SMA and Inner ROC is also positive, signals
a trend continuation with increasing velocity -- adapted here as a
long-only trend-continuation entry with a symmetric deceleration/trend-break
exit and a 15-day time-stop.

**Source:** https://www.tradingview.com/script/1aIO35U8-Double-ROC-Acceleration-by-Ocean-Drive/
(also checked https://www.tradingview.com/script/qyMkrkEP-Delta-ROC-acceleration-Guide/ -- page removed/ghosted, no content)

**Strategy file:** `strategies/2026-09-06_double_roc_acceleration_trend.py`

## Step 6 grid summary (`run_strategy_grid`)

- Grid: `inner_len` in {15, 25, 35} x `trend_window` in {50, 100} x symbols
  {QQQ, SPY, BTC/USDT, ETH/USDT} x vol regimes {low, mid, high}
- **72 total cells, 14 passed -- pass_fraction = 0.194**
- by_asset_class: equity 14/36 (39%), crypto 0/36 (0%)
- by_vol_regime: low 9/24 (37.5%), mid 4/24 (16.7%), high 1/24 (4.2%)
- best_cell: SPY, inner_len=25, trend_window=100, **low-vol regime, Sharpe=2.42**
- worst_cell: QQQ, inner_len=15, trend_window=100, high-vol regime, Sharpe=-1.69

The strategy shows a real, concentrated edge: equity-only, and strongly
skewed toward low-volatility regimes (accelerating momentum works well when
markets are calm, degrades in high-vol/choppy conditions where "acceleration"
signals whipsaw). Crypto sees zero passing cells across the entire grid.

## Step 7 single-config validators (best grid combo full-sample: SPY, inner_len=25, trend_window=100)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full sample, all regimes combined) | 0.690 | >= 1.0 | FAIL |
| Max drawdown | 0.112 | <= 0.25 | PASS |
| Transaction cost survival (net Sharpe, 10bps/trade, 92 trades) | 0.380 | >= 0.5 | FAIL |
| Parameter sensitivity (relative std across 6 inner_len x trend_window combos) | 0.335 | <= 0.5 | PASS |
| Walk-forward | not run | -- | `check_walk_forward` is currently broken in the installed vectorbt version (`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`) -- pre-existing tooling issue affecting every strategy in this repo, not specific to this one. |

Note the discrepancy: the grid's best-cell Sharpe (2.42) is measured on the
low-vol-regime SLICE only, while the full-sample Sharpe (0.69) blends in the
mid/high-vol periods where the strategy loses money -- this is exactly the
"narrower-but-honest" scope the grid step is meant to surface.

## Decision: REJECT (full-sample), but flag as a promising narrow-scope near-miss

Full-sample Sharpe and transaction-cost-adjusted Sharpe both fail on the
best overall config. However this is NOT a decisive/uniform rejection like
prior iterations: it's an equity-only, low-vol-regime-concentrated edge
(9/24 low-vol cells passed vs. 1/24 high-vol) with reasonable parameter
stability. A future iteration could revisit this by (a) explicitly gating
entries to only fire during low-vol regimes (like the accepted
`2026-09-03_bb_meanrev_qqq_volregime.py` pattern), which would likely lift
the full-sample Sharpe close to or above the 2.42 low-vol-only figure, and
(b) dropping crypto entirely, which contributed 0 passing cells.
