# Backtest Report: Weekly-Filtered Daily MACD Crossover + Price-Action Trailing Exit

**Strategy file:** `strategies/2026-09-12_quantpedia_d1h1_trail_weekly_daily.py`
**Hypothesis ID:** 2026-09-12-192
**Source:** https://quantpedia.com/how-to-design-a-simple-multi-timeframe-trend-strategy-on-bitcoin/
(David Mesíček, Quantpedia, Nov 2025)

## Hypothesis

Source's own step-by-step improvement on Bitcoin (hourly bars): bare MACD
crossover (Sharpe 0.33) -> add Elder Triple-Screen-style higher-timeframe
(Daily) trend filter (Sharpe 0.80) -> add price-action trailing exit
("hold while bars close green, exit on first red bar") (Sharpe 1.07).
Adapted to this repo's daily-bar data by shifting both timeframes up one
level: Weekly MACD trend filter gates Daily MACD crossover entries, with
the same price-action trailing exit.

## Grid test (Step 6): `fast_period` in {8,12} x `slow_period` in {21,26}
(`signal_period` fixed at source's literal 9), QQQ/SPY equity + BTC/USDT,
ETH/USDT crypto, vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.104** (5/48 cells) -- weak result.
- **By asset class:** equity 5/24; crypto 0/24 (decisive fail).
- **By vol regime:** low 0/16, mid 5/16, high 0/16 -- unusually, edge (what
  little exists) is concentrated in the MID-vol tercile rather than
  low-vol as is typical for other trend strategies in this repo.
- **Best cell:** QQQ, mid-vol, `fast=8, slow=21` (Sharpe 1.59).
- **Worst cell:** QQQ, high-vol, `fast=8, slow=21` (Sharpe -1.25) -- same
  config swings from best to worst cell depending on vol regime, a red
  flag for regime instability.
- **Best average-Sharpe config across vol regimes:** SPY `fast=12,
  slow=26` avg Sharpe only **0.595** -- well below the 1.0 min_sharpe
  threshold even for the best config/symbol combination.

## Decision: **REJECT (decisive)** -- no single-config validator run

The best-performing config's own across-vol-regime average Sharpe (0.595)
falls well short of the 1.0 minimum threshold, and the same top-cell
config (QQQ fast=8/slow=21) flips from the grid's best cell (mid-vol,
Sharpe 1.59) to its worst cell (high-vol, Sharpe -1.25), indicating the
apparent edge is a regime-specific artifact rather than a robust signal.
Per RESEARCH_LOOP.md Step 8, rejected without a full Step 7 single-config
validator run since the grid result clearly fails the headline bar. The
timeframe-shift adaptation (Hourly/Daily source -> Daily/Weekly here) may
itself be a contributing factor -- the source's own reported edge stacks
up over a much finer 1H granularity that daily bars cannot replicate
one-for-one.
