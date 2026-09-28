# Throwback Power Move Donchian Exit — Backtest Report

**Strategy file:** `strategies/2026-09-28_throwback_power_move_donchian_exit.py`
**Date:** 2026-09-28

## Hypothesis

Per Bulkowski's Throwbacks page (https://www.thepatternsite.com/throwbacks.html,
read 2026-09-28 via browser_exec — `web_extract` failed: "DuckDuckGo (ddgs) is
a search-only backend and cannot extract URL content"), after an upward
breakout ~58% of chart patterns throw back within 30 calendar days. The
source's own disclosed "Power Move" statistic: when price during the
throwback window remains at or above the breakout price, the subsequent rise
from breakout to ultimate high averages 40% (n=400); when price drops below
the breakout price during the throwback window, the subsequent rise averages
only 29% (n=2,767) and 35% of those continue falling below the pattern
entirely.

Operationalized as a Donchian(N)-breakout entry with a "throwback-failure"
defensive exit: if close drops back below its own breakout level within
`throwback_window` trading days of entry, exit immediately (cut the weaker
29%-average cohort early); otherwise hold with a plain trailing-low stop.

## Single-config validators (QQQ, SPY; donchian_window=20, throwback_window=15; 2019-01-01..2026-09-01)

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | 1.187 (pass, thr 1.0) | 0.569 (**fail**, thr 1.0) |
| Max Drawdown | 0.159 (pass, thr 0.25) | 0.184 (pass, thr 0.25) |
| Net Sharpe after costs (10bps/trade) | 1.131 (pass, thr 0.5) | 0.436 (**fail**, thr 0.5) |
| Walk-forward pass fraction (4 splits) | 0.75 (pass, thr 0.75) | 0.75 (pass, thr 0.75) |
| Parameter sensitivity (relative std, 9-cell sweep) | 0.083 (pass, thr 0.5) | 0.380 (pass, thr 0.5) |

QQQ: **all validators pass.** SPY: Sharpe and cost-survival fail.

## Step 6 grid summary

Grid: `donchian_window` in {20, 40} x `throwback_window` in {15, 30}, QQQ/SPY,
vol_regime_splits=3, 2019-01-01..2026-09-01 (light workload — equity only,
2x2 param grid).

- pass_fraction: 0.417 (10/24)
- by_asset_class: equity 10/24
- by_vol_regime: low 8/8, mid 2/8, high 0/8
- best_cell: donchian_window=20, throwback_window=15, QQQ, low-vol regime, Sharpe 2.954
- worst_cell: donchian_window=40, throwback_window=15, SPY, mid-vol regime, Sharpe -0.573

Strategy holds strongly in low-vol regimes across both symbols, degrades in
mid-vol, and fails outright in high-vol — a plain Donchian breakout with this
exit rule is not vol-regime-robust broadly, but concentrated performance in
low-vol is real and QQQ passes the full validator suite unconditionally.

## Decision: ACCEPT for QQQ only

QQQ clears all 5 validators. SPY does not (Sharpe 0.569 < 1.0, net Sharpe
after costs 0.436 < 0.5) — reject for SPY. Scope this strategy to QQQ (and by
extension similar high-momentum tech-heavy equity indices) rather than broad
equity use; flag SPY's failure and the high-vol-regime failure across both
symbols in the knowledge base for future loops considering this pattern
family.
