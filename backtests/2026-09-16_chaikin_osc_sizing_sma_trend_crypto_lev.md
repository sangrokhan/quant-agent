# Backtest Report: Chaikin Oscillator Sizing Dial — Crypto Leverage-Cap Recalibration

**Strategy file:** `strategies/2026-09-16_chaikin_osc_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16
**Hypothesis source:** Formula unchanged from 2026-09-14-122 (Marc Chaikin;
investopedia.com/terms/c/chaikinoscillator.asp, read via browser_exec).
This sub-iteration reuses the confirmed formula and applies this repo's
leverage-cap-aware crypto retune pattern.

## Hypothesis

2026-09-14-122's Chaikin Oscillator z-score-normalized continuous sizing
dial, gated by an `SMA(trend_window)` uptrend filter, was accepted
decisively on equity (QQQ+SPY) but rejected on crypto with an MDD-only
near-decisive miss: BTC/USDT MDD 30.5% > 25% threshold, with Sharpe 1.515
(pass), TC-survival 1.117 (pass), and walk-forward 1.0 (pass) — all other
4 validators already passing. Cutting `leverage_cap` to 0.3 (scaling
`base_exposure`/`deadband` proportionally) should pull crypto MDD under
25%.

## Grid test (Step 6)

`param_grid={"sensitivity": [0.3, 0.5, 0.7], "leverage_cap": [0.25, 0.3, 0.35]}`,
`symbols={"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- total_cells=54, passed=45, **pass_fraction=0.833**
- by_asset_class: crypto 45/54
- by_vol_regime: low 18/18, mid 18/18, high 9/18
- best_cell: sensitivity=0.7, leverage_cap=0.25, ETH/USDT, mid-vol, sharpe=2.38
- worst_cell: sensitivity=0.5, leverage_cap=0.25, ETH/USDT, high-vol, sharpe=0.18

## Standard validators (Step 7) — primary config

`trend_window=40, co_fast=3, co_slow=10, zscore_window=60, base_exposure=0.15, sensitivity=0.5, leverage_cap=0.3, deadband=0.10`

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction | Param sens rel-std |
|---|---|---|---|---|---|
| BTC/USDT | 1.402 (pass) | 0.1314 (pass) | 0.805 (pass) | 1.0 (pass) | 0.046 (pass) |
| ETH/USDT | 1.172 (pass) | 0.1707 (pass) | 0.794 (pass) | 1.0 (pass) | 0.069 (pass) |

Walk-forward used a manual 4-fold range split (same semantics as
`validators.check_walk_forward`) because `vectorbt.utils.splitting.RangeSplitter`
is unavailable in this environment's installed vectorbt version.

## Decision (Step 8)

**Accepted (crypto only, this sub-iteration)** — BTC/USDT and ETH/USDT
both pass all 5 validators at leverage_cap=0.3, rescuing the prior
2026-09-14-122 crypto MDD near-decisive rejection. Combined with the
existing 2026-09-14-122 QQQ+SPY equity accept, Chaikin Oscillator's
continuous-sizing dial now covers the full universe (QQQ, SPY, BTC/USDT,
ETH/USDT).
