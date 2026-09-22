# 2026-09-22 — Elliott Wave 3 Entry (pullback + breakout confirmation)

**Hypothesis**: Source: https://algobars.com/strategy-templates/elliott/wave-3-entry/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Elliott Wave 3 ("typically the longest and strongest impulse
wave"): identify a completed Wave 1 impulse (swing-low-to-swing-high), wait
for a Wave 2 retracement of 50-78.6% of Wave 1 (without breaking below the
Wave 1 start), then enter long on a breakout above the Wave 1 high,
targeting a 1.618x Fibonacci extension of Wave 1's length. Distinct from
this repo's existing Fibonacci-retracement entry (2026-09-03-022,
near-miss rejected) which buys DURING the retracement (mean-reversion
style, no breakout confirmation, open-ended "new swing high" exit) --
this strategy instead waits for the retracement to complete and enters on
breakout confirmation (trend-continuation style) with a fixed
Fibonacci-extension profit target.

**Strategy file**: `strategies/2026-09-22_elliott_wave3_breakout.py`

**Grid test** (`run_grid_elliott_wave3_breakout.py`): param_grid =
`{pivot_window: [3, 5, 8], extension_mult: [1.272, 1.618, 2.0]}`,
symbols = equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), vol_regime_splits=3.
- total_cells=108, passed_cells=13, pass_fraction=0.120
- by_asset_class: equity 7/54, crypto 6/54
- by_vol_regime: low 5/36, mid 2/36, high 6/36 -- no single vol regime
  dominates, but each passing param combo passes in only ONE vol tercile
  (never generalizes across regimes for the same symbol/config)
- best_cell: QQQ pivot_window=3/extension_mult=1.618, low-vol, Sharpe 1.79
  (per-tercile only)

**Single-config validators** (full-sample 2019-2026, config
`pivot_window=3, extension_mult=1.618`):

| Metric | QQQ | ETH/USDT | Threshold |
|---|---|---|---|
| Sharpe ratio | -0.155 (FAIL) | 0.892 (near-miss FAIL) | ≥1.0 |
| Max drawdown | 0.134 (pass) | 0.232 (pass) | ≤0.25 |
| TX-cost survival (10bps/trade) | -0.207 (FAIL) | 0.877 (pass) | ≥0.5 |
| Trade count | 10 | 22 | -- |

**Decision**: REJECTED (all symbols). QQQ's promising low-vol-tercile grid
cell (Sharpe 1.79) completely inverts full-sample (Sharpe -0.155) with only
10 trades over the full 2019-2026 window -- a clear small-sample artifact,
not a real edge. ETH/USDT is a genuine near-miss (Sharpe 0.892, passes
MDD and TX-cost survival) but falls short of the 1.0 threshold. No
parameter combination passed more than one vol-regime tercile for the same
symbol, indicating the "impulse-retrace-breakout" mechanic doesn't produce
a consistent edge across market conditions even where isolated grid cells
looked strong.
