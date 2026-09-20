# Toby Crabel "Down Thrust" traded LONG (counterintuitive) — Backtest Report

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_crabel_downthrust_long_bias.py`
**Source:** https://statoasis.com/overfit/research/unveiling-toby-crabel-s-up-down-thrust-trading-patterns (Ali Casey, StatOasis, 17,424-backtest study)

## Hypothesis

Crabel's "down thrust" pattern (pivot low, then a bar opens below the pivot
low, closes above each of the previous two closes, and closes in the upper
half of its own range) is conventionally read bearish. The source's own
large-scale measurement found the opposite: pooled across 8 markets, the
next 20 bars after a down thrust averaged +0.94% vs +0.42% for an average
day; traded SHORT it was only a coin-flip (47.8% win rate). This strategy
tests going LONG after a down-thrust bar, with the source's own
best-performing exit overlay (RSI(2) exit, source found lifts win rate
50.0%→62.3%) plus a max_hold_days time-stop backstop.

## Grid test summary (Step 6)

144 cells: `pivot_left∈{4,10} × rsi_exit_level∈{55,65,75} ×
max_hold_days∈{10,20}` on equity {QQQ,SPY} and crypto {BTC/USDT,ETH/USDT},
3 vol-regime terciles, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.0 (0/144) — decisive fail across every dimension**
- by_asset_class: equity 0/72, crypto 0/72
- by_vol_regime: low 0/48, mid 0/48, high 0/48
- best_cell: pivot_left=4, rsi_exit_level=55, max_hold_days=10, QQQ, low-vol, Sharpe 0.842 (still below threshold)
- worst_cell: ETH/USDT, low-vol, Sharpe -1.38

## Decision: **REJECTED** (decisive — no single-config validation run, grid already conclusive)

Not a single one of 144 grid cells clears the Sharpe≥1.0 threshold, and the
best cell (0.842) falls well short. This is consistent with the source's
own finding that the down-thrust's directional edge, even at its stated
best construction (short side, RSI(2) exit), is only marginally better than
a coin flip (47.8% win rate) — the source never actually recommends going
LONG after a down thrust; this iteration's inversion hypothesis (exploiting
the source's aggregate pooled statistic literally) does not survive
single-symbol daily-bar backtesting on QQQ/SPY/BTC/ETH.
