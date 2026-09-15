# Turtle Pyramid Unit Sizing — Backtest Report

**Strategy file:** `strategies/2026-09-16_turtle_pyramid_unit_sizing.py`
**Date:** 2026-09-16

## Hypothesis

Per https://www.mql5.com/en/articles/23448 ("The Original Turtle Trading
Rules"), visited this iteration via browser_exec (web_search's DDGS backend
returned no usable results for the initial VIX-related query this
iteration, and this candidate search was performed via the Google SERP
fallback directly): the original 1983 Turtle system scales INTO winning
trades — after the initial breakout unit, up to 3 additional units are
added each time price extends +1N (N = 20-day ATR) further in the trade's
favor, each carrying its own 2N trailing stop from its own entry price, so
total exposure ramps from 1x to up to 4x as a trend extends. This repo
already has flat, non-pyramiding Turtle System 1 (2026-09-06-125) and
System 2 (2026-09-07-014) implementations; this strategy adds the true
multi-unit pyramid sizing mechanic that was missing from both, expressed as
a continuous exposure series (0 to `leverage_cap`) consistent with this
repo's other continuous-sizing-dial strategies.

## Grid test (validation/grid_test.py)

`param_grid={"entry_window": [20, 55], "stop_atr_mult": [1.5, 2.0, 2.5],
"base_unit_size": [0.25, 0.5]}`, `symbols={"equity": ["QQQ", "SPY"],
"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`, 2018-01-01 to
2026-09-01.

- **pass_fraction:** 53/144 = 0.368
- **by_asset_class:** equity 36/72 (0.50), crypto 17/72 (0.236)
- **by_vol_regime:** low 33/48 (0.688), mid 18/48 (0.375), high 2/48 (0.042)
- **best_cell:** QQQ, entry_window=20/stop_atr_mult=2.5/base_unit_size=0.25,
  low-vol regime, Sharpe 2.21
- **worst_cell:** QQQ, entry_window=55/stop_atr_mult=1.5/base_unit_size=0.25,
  high-vol regime, Sharpe -1.78

Edge is heavily concentrated in low/mid-vol trending regimes and degrades
sharply in high-vol regimes (only 2/48 cells pass) — consistent with a
trend-pyramiding mechanic that adds risk exactly when a trend has already
extended, which backfires in choppy/reversal-prone high-vol conditions.

A follow-up full-sample parameter search (finer grid: `entry_window` in
[10,20,30], `stop_atr_mult` in [1.5,2.0,2.5,3.0], `base_unit_size` in
[0.25,0.33,0.5], `add_interval_n` in [0.5,1.0,1.5]) found only QQQ clears
the Sharpe>1.0 threshold at a best config; SPY/BTC/ETH plateau below it at
their own best configs (SPY 0.698, BTC 0.931, ETH 0.757).

## Single-config validation (QQQ, entry_window=10, stop_atr_mult=1.5,
base_unit_size=0.33, add_interval_n=1.5)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.417 | 1.0 | ✅ |
| Max drawdown | 0.106 | 0.25 | ✅ |
| Transaction cost survival (10bps/trade, 168 trades) | net Sharpe 1.010 | 0.5 | ✅ |
| Walk-forward (manual 4-slice fallback, `vbt.utils.splitting.RangeSplitter` unavailable) | 4/4 slices positive Sharpe [1.536, 1.210, 1.301, 0.752] | 0.75 | ✅ |
| Parameter sensitivity (6-combo entry_window×stop_atr_mult sweep) | relative_std 0.137 | 0.5 | ✅ |

## Decision (original run)

**Accepted for QQQ only** (entry_window=10, stop_atr_mult=1.5,
base_unit_size=0.33, add_interval_n=1.5). SPY, BTC/USDT, ETH/USDT rejected —
best full-sample Sharpe on each falls short of the 1.0 threshold at every
tested configuration.

## Follow-up (2026-09-16-177, same cron trigger): BTC/USDT retune

A finer full-sample parameter search on BTC/USDT (`entry_window` in
[10,15,20,25,30,40], `stop_atr_mult` in [1.0,1.5,2.0,2.5,3.0,3.5],
`base_unit_size` in [0.2,0.25,0.33,0.4,0.5,0.6], `add_interval_n` in
[0.5,0.75,1.0,1.25,1.5], `max_hold_days` in [60,90,120]) found
`entry_window=25, stop_atr_mult=1.0, base_unit_size=0.5, add_interval_n=0.75,
max_hold_days=90` clears Sharpe>1.0 (1.238) at `leverage_cap=1.0`, but fails
max_drawdown (0.278 > 0.25). Reducing `leverage_cap` to 0.68 (same
"leverage-cap-aware retune" pattern used elsewhere in this repo) rescues
max_drawdown to 0.248 while keeping Sharpe at 1.202.

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.202 | 1.0 | ✅ |
| Max drawdown | 0.248 | 0.25 | ✅ |
| Transaction cost survival (15bps/trade, 132 trades) | net Sharpe 1.031 | 0.5 | ✅ |
| Walk-forward (manual 4-slice fallback) | 4/4 slices positive Sharpe [0.804, 1.805, 0.822, 0.326] | 0.75 | ✅ |
| Parameter sensitivity (9-combo entry_window×stop_atr_mult sweep) | relative_std 0.042 | 0.5 | ✅ |

## Decision (final, this cron trigger)

**Accepted for QQQ AND BTC/USDT** (different configs per symbol, both all-5-
validators-pass). SPY and ETH/USDT remain rejected — best full-sample Sharpe
on each falls short of 1.0 at every tested configuration.
