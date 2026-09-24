# Backtest Report: Dead Cat Bounce Short-the-Fade (QQQ, SPY)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_dead_cat_bounce_short.py`
**Sources:** Google SERP snippets of https://www.dxpa.in (full page 404s) and https://www.thinkmarkets.com (full article 404s) — both browser_exec

## Hypothesis
Per SERP-disclosed rules: after a sharp multi-day decline (>=X% over a few
days on heavy volume), a shallow bounce (small % retrace, on lighter
volume) is a "dead cat bounce" that should fail and the downtrend should
resume — short the weak bounce, target a new low, stop out if price
reclaims the bounce high. Zero prior "dead cat bounce" entries in this
repo. Original SERP-disclosed thresholds (10-20% decline, 3-5% bounce) were
too rare to test on daily QQQ/SPY bars (0-2 signals over 7.5yr), so
calibrated down to decline_pct in {0.03, 0.04, 0.05} for a testable sample
size — an explicit, disclosed deviation from the source's own numbers.

## Grid summary (Step 6)
`param_grid={"decline_pct": [0.03, 0.04, 0.05], "max_hold_days": [5, 10]}`,
`symbols={"equity": ["QQQ", "SPY"]}`, `vol_regime_splits=3` (light workload).

- total_cells: 36, passed_cells: 0, **pass_fraction: 0.0**
- All vol regimes: 0/12 pass (low, mid, high all fail)
- best_cell: decline_pct=0.03, max_hold_days=10, QQQ, low-vol, Sharpe **-0.079** (still negative)
- worst_cell: same params, QQQ, high-vol, Sharpe -1.587

## Decision: REJECT (decisive, all cells negative Sharpe)
Even the best grid cell has negative Sharpe. Shorting shallow bounces after
small declines does not have a positive edge on daily QQQ/SPY bars at any
tested calibration. No single-config validator run performed — grid result
alone is decisive (pass_fraction 0.0, best cell still negative).
