# Backtest Report: Twiggs Money Flow Sizing Dial — Crypto Leverage-Cap Recalibration

**Strategy file:** `strategies/2026-09-16_tmf_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16
**Hypothesis source:** Formula unchanged from 2026-09-14-123 (Colin
Twiggs; incrediblecharts.com, read via browser_exec). This sub-iteration
reuses the confirmed formula and applies this repo's leverage-cap-aware
crypto retune pattern.

## Hypothesis

2026-09-14-123's Twiggs Money Flow continuous sizing dial, gated by an
`SMA(trend_window)` uptrend filter, was accepted decisively on equity
(QQQ+SPY) but rejected on crypto with an MDD-only miss: BTC/USDT MDD 31.4%
> 25% threshold, with Sharpe 1.514 (pass), TC-survival 1.364 (pass), and
walk-forward 1.0 (pass) — all other 4 validators already passing. Cutting
`leverage_cap` to 0.3 (scaling `base_exposure`/`deadband` proportionally)
should pull crypto MDD under 25%.

## Grid test (Step 6)

`param_grid={"sensitivity": [0.3, 0.5, 0.7], "leverage_cap": [0.25, 0.3, 0.35]}`,
`symbols={"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- total_cells=54, passed=45, **pass_fraction=0.833**
- by_asset_class: crypto 45/54
- by_vol_regime: low 18/18, mid 18/18, high 9/18
- best_cell: sensitivity=0.3, leverage_cap=0.25, ETH/USDT, mid-vol, sharpe=2.48
- worst_cell: sensitivity=0.3, leverage_cap=0.25, ETH/USDT, high-vol, sharpe=0.42

## Standard validators (Step 7) — primary config

`trend_window=40, tmf_window=21, base_exposure=0.15, sensitivity=0.5, leverage_cap=0.3, deadband=0.10`

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction | Param sens rel-std |
|---|---|---|---|---|---|
| BTC/USDT | 1.468 (pass) | 0.0998 (pass) | 0.875 (pass) | 1.0 (pass) | 0.003 (pass) |
| ETH/USDT | 1.260 (pass) | 0.1228 (pass) | 0.879 (pass) | 1.0 (pass) | 0.0002 (pass) |

Walk-forward used a manual 4-fold range split (same semantics as
`validators.check_walk_forward`) because `vectorbt.utils.splitting.RangeSplitter`
is unavailable in this environment's installed vectorbt version.

## Decision (Step 8)

**Accepted (crypto only, this sub-iteration)** — BTC/USDT and ETH/USDT
both pass all 5 validators at leverage_cap=0.3, rescuing the prior
2026-09-14-123 crypto MDD rejection. Combined with the existing
2026-09-14-123 QQQ+SPY equity accept, Twiggs Money Flow's continuous-sizing
dial now covers the full universe (QQQ, SPY, BTC/USDT, ETH/USDT).
