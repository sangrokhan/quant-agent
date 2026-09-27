# Wyckoff Markup Breakout Pullback Confirm — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_wyckoff_markup_breakout_pullback_confirm.py`
**Source:** https://www.luxalgo.com/library/indicator/markup-and-markdown/

## Hypothesis

LuxAlgo's "Markup & Markdown" dates the Wyckoff cycle's trending phases
with explicit confirmation discipline: a compressed range must exist
first, an exit on widening spread + expanding volume prints a
Sign-of-Strength breakout, and the phase only fully CONFIRMS once the
first pullback holds beyond the old range boundary (doesn't fall back
inside). Implemented long-only as a two-stage compression -> SOS-breakout
-> pullback-confirmation entry sequence, exiting when close falls back
below the (now-support) old boundary or a time-stop.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`max_range_atr_mult in {3.5,5.0,8.0}` x `widening_spread_threshold in {1.0,1.25}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.083 (6/72)**
- by_asset_class: equity 0/36, crypto 6/36 (all mid-vol)
- by_vol_regime: low 0/24, mid 6/24, high 0/24

## Signal-frequency and full-sample checks

Equity (QQQ, SPY): even at the loosest tested setting
(`max_range_atr_mult=8.0`), only 5-6 trades fire over the full 7.7-year
window — too rare for statistical validity (same signal-scarcity pattern
as this trigger's Parabolic Phase entry).

Crypto (BTC/USDT, ETH/USDT): adequate trade counts (168, 197 respectively)
at the default config, but full-sample Sharpe is decisively near zero
(BTC -0.003, ETH 0.056), and ETH's max drawdown (0.302) also fails the
0.25 threshold.

## Decision

**Rejected.** Equity's signal is too rare to trust despite zero passing
cells anyway (0/36); crypto has an adequate sample but a genuinely flat
edge (Sharpe ~0) and excessive drawdown on ETH. Neither asset class
supports acceptance.

## Notes for future loops

Unlike the "Trading-range Position" strategy tested earlier this same
cron trigger (which trades WITHIN a compressed range and had at least a
detectable, if narrow, equity edge), this breakout-WITH-pullback-
confirmation construction shows no edge on crypto and is too rare on
equity to evaluate. The pullback-confirmation discipline itself (waiting
for the "back-up" to hold) may be sound in principle but this daily-bar
proxy implementation doesn't capture enough setups to prove it either way
on equity; a future loop with intraday data or a much longer equity
universe (individual growth stocks rather than QQQ/SPY only) might get a
fairer test.
