# Backtest Report: Bulkowski W-Setup Double-Support-Retest (2026-09-26)

## Hypothesis
Source: Thomas Bulkowski's thepatternsite.com/WSetup.html (browser_exec,
free, fully disclosed, source's own stat: 62% win rate on 78 trades).

After a multi-month decline from swing high A, price finds support at B
(any pattern shape). Price recovers, then retraces back down to a SECOND
support test at C near the same price level as B (a "W" shape). Buy once
support visibly holds a second time at C; stop below min(B,C).

Operationalized: rolling local-low detection for B, `recovery_pct`
confirmation, retest for C within `support_tolerance_pct` of B within
`retest_window` bars, entry on a `confirm_pct` bounce off C; exit via
`stop_pct`/`target_pct`/`max_hold_days`.

First double-support-retest (two time-separated support tests, no breakout
confirmation) strategy in this repo -- distinct from double-bottom
strategies requiring a neckline breakout.

## Grid test summary (Step 6)

`support_tolerance_pct in {0.03, 0.05} x target_pct in {0.10, 0.15, 0.20}`,
QQQ/SPY/BTC-USDT/ETH-USDT, `vol_regime_splits=3`, 2016-01-01 to 2026-09-01:

- `pass_fraction = 0.111` (8/72)
- `by_asset_class`: equity 6/36, crypto 2/36
- `by_vol_regime`: low 8/24, mid 0/24, high 0/24 -- classic vol-regime-slicing
  mirage (only the thin low-vol tercile clears the bar)
- `best_cell`: support_tolerance_pct=0.05, target_pct=0.15, QQQ, low-vol,
  Sharpe 1.403
- `worst_cell`: support_tolerance_pct=0.05, target_pct=0.15, BTC/USDT,
  mid-vol, Sharpe -1.288

Full local 6-combo full-sample sweep (no vol slicing):
- QQQ: 0.449 to 0.631 (never clears 1.0)
- SPY: 0.198 to 0.630 (never clears 1.0; also very low trade count, 4-6
  trades over 10.5 years)
- BTC/USDT: 0.062 to 0.464 (never clears 1.0)
- ETH/USDT: -0.299 to 0.059 (negative/near-zero across the board)

## Decision: REJECTED (all symbols)

Full-sample Sharpe never clears the 1.0 threshold for ANY symbol at ANY
tested configuration -- a decisive rejection, not a near-miss. Additionally
trade counts are very low (4-22 over a 10.5-year window depending on
symbol/config), consistent with the source's own pattern being genuinely
rare (a multi-month-separated double support test is a much stricter
condition than a standard double bottom). Not pursued further given the low
signal density and consistently sub-threshold Sharpe across the entire
local parameter neighborhood.

Source: https://thepatternsite.com/WSetup.html (browser_exec, free, fully
disclosed).
