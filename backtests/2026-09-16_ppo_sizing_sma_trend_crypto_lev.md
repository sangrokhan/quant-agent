# Backtest Report: PPO Sizing Dial — Crypto Leverage-Cap Recalibration

**Strategy file:** `strategies/2026-09-16_ppo_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16
**Hypothesis source:** Formula unchanged from 2026-09-14-110 (Percentage
Price Oscillator; StockCharts/Investopedia/TrendSpider/Composer via Google
SERP). This sub-iteration reuses the confirmed formula and applies this
repo's leverage-cap-aware crypto retune pattern.

## Hypothesis

2026-09-14-110's PPO z-score/tanh continuous sizing dial, gated by an
`SMA(trend_window)` uptrend filter, was accepted decisively on equity
(QQQ+SPY, first PPO accept in this repo) but rejected on crypto: BTC/USDT
MDD 44.5% > 25% threshold, one of the larger crypto MDD misses recorded
in this repo, with leverage_cap left at the equity default 1.0. Given the
larger original miss, `leverage_cap` was cut slightly tighter (0.25) than
the repo's usual 0.3, with `base_exposure`/`deadband` scaled down
proportionally.

## Grid test (Step 6)

`param_grid={"ppo_sensitivity": [0.4, 0.6, 0.8], "leverage_cap": [0.2, 0.25, 0.3]}`,
`symbols={"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- total_cells=54, passed=45, **pass_fraction=0.833**
- by_asset_class: crypto 45/54
- by_vol_regime: low 18/18, mid 18/18, high 9/18
- best_cell: ppo_sensitivity=0.6, leverage_cap=0.2, ETH/USDT, mid-vol, sharpe=2.09
- worst_cell: ppo_sensitivity=0.8, leverage_cap=0.3, ETH/USDT, high-vol, sharpe=0.42

## Standard validators (Step 7) — primary config

`trend_window=40, ppo_fast=12, ppo_slow=26, ppo_zscore_window=100, base_exposure=0.12, ppo_sensitivity=0.6, leverage_cap=0.25, deadband=0.08`

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction | Param sens rel-std |
|---|---|---|---|---|---|
| BTC/USDT | 1.265 (pass) | 0.1179 (pass) | 0.842 (pass) | 1.0 (pass) | 0.035 (pass) |
| ETH/USDT | 1.089 (pass) | 0.1229 (pass) | 0.787 (pass) | 1.0 (pass) | 0.063 (pass) |

Walk-forward used a manual 4-fold range split (same semantics as
`validators.check_walk_forward`) because `vectorbt.utils.splitting.RangeSplitter`
is unavailable in this environment's installed vectorbt version.

## Decision (Step 8)

**Accepted (crypto only, this sub-iteration)** — BTC/USDT and ETH/USDT
both pass all 5 validators at leverage_cap=0.25, rescuing the prior
2026-09-14-110 crypto MDD rejection (a decisive 44.5% miss). Combined with
the existing 2026-09-14-110 QQQ+SPY equity accept, PPO's continuous-sizing
dial now covers the full universe (QQQ, SPY, BTC/USDT, ETH/USDT).
