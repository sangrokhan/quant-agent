# Turtle Soup Liquidity-Sweep Reversal — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_turtle_soup_liquidity_sweep_reversal.py`
**Source:** https://grandalgo.com/blog/ict-turtle-soup-strategy (read via web_search + browser_exec-style extraction of the article body)

## Hypothesis

Linda Raschke's "Turtle Soup" fade of the original Turtle Traders' N-day
breakout system: when price sweeps below (above) a well-respected N-bar
swing low (high) — triggering stop-losses/breakout entries clustered there —
but fails to continue and closes back inside the prior range within a few
bars, that reclaim close is a high-probability long (short) reversal entry.
Stop below the sweep extreme (not the original swing low), target a
reward:risk multiple of the stop distance, plus a time-stop.

Implemented long-only: `swing_lookback`-day rolling low as the reference
level, `reclaim_window`-bar window to wait for the reclaim close,
`reward_r_multiple` R target, `max_hold_days` time-stop.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`, param_grid
`swing_lookback in {10,20,30}` x `reward_r_multiple in {1.5,2.0,3.0}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.0648 (7/108)**
- by_asset_class: equity 7/54, crypto 0/54
- by_vol_regime: low 7/36, mid 0/36, high 0/36
- best_cell: QQQ, swing_lookback=10, reward_r_multiple=3.0, low-vol, Sharpe 2.13
- worst_cell: ETH/USDT, swing_lookback=20, reward_r_multiple=3.0, high-vol, Sharpe -1.05

Only 7 of 108 cells passed the grid's per-cell Sharpe>=1.0/MDD<=0.25
threshold, all equity, all low-vol-tercile. Crypto failed decisively across
every combination and vol regime; equity fails outside the low-vol tercile.

## Single-config validators (best cell: QQQ, swing_lookback=10, reward_r_multiple=3.0, full sample)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.468 | >= 1.0 | **FAIL** |
| Max drawdown | 0.232 | <= 0.25 | pass |
| Transaction cost survival (10bps/trade, 94 trades) | net Sharpe 0.338 | >= 0.5 | **FAIL** |

Full-sample (not just the low-vol tercile) Sharpe on QQQ is well below the
1.0 threshold once the mid/high-vol regimes are included, and it fails
transaction-cost survival as well.

## Decision

**Rejected.** The apparent edge (grid pass_fraction 0.065, best-cell Sharpe
2.13) is entirely an artifact of the low-vol tercile on equities; full-sample
Sharpe/TC checks fail decisively, and crypto is a total washout (0/54 cells).
This is consistent with the repo's existing near-duplicate finding
(`2026-09-04-076`, plain rolling-N-day-low fade, pass_fraction 0.042) and
`2026-09-26-043` (aged-level Turtle Soup variant) — the sweep-and-reclaim
family appears to only work in narrow calm-market slices, not as a general
edge, even with the R-multiple bracket exit and reclaim-window addition
tried here.

## Notes for future loops

A future iteration could try gating this pattern explicitly with a
choppiness/ADX<20 sideways-regime filter (as the prior 2026-09-04-076 entry
also suggested) rather than relying on volatility tercile alone, since low
realized-vol and range-bound/mean-reverting conditions aren't identical.
