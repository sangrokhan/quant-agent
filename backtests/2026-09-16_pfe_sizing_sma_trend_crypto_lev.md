# Backtest Report: PFE Sizing Dial — Crypto Leverage-Cap Recalibration

**Strategy file:** `strategies/2026-09-16_pfe_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16
**Hypothesis source:** Formula unchanged from 2026-09-14-102 (Polarized
Fractal Efficiency, Hans Hannula 1994; read directly from Investopedia via
browser_exec). This sub-iteration reuses the confirmed formula and applies
this repo's leverage-cap-aware crypto retune pattern.

## Hypothesis

2026-09-14-102's PFE continuous sizing dial, gated by an
`SMA(trend_window)` uptrend filter, was accepted decisively on equity
(QQQ+SPY) but rejected on crypto with MDD "pinned" at 29.6-30.7% across
every deadband widening tried (0.25-0.30) — explicitly flagged in the
prior entry as resistant to deadband widening alone. Cutting `leverage_cap`
to 0.3 (scaling `base_exposure`/`deadband` down proportionally) should pull
crypto MDD under 25% since the fix needed is a tighter exposure ceiling,
not a wider rebalance band.

## Grid test (Step 6)

`param_grid={"pfe_sensitivity": [0.4, 0.6, 0.8], "leverage_cap": [0.25, 0.3, 0.35]}`,
`symbols={"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- total_cells=54, passed=45, **pass_fraction=0.833**
- by_asset_class: crypto 45/54
- by_vol_regime: low 18/18, mid 18/18, high 9/18
- best_cell: pfe_sensitivity=0.8, leverage_cap=0.35, ETH/USDT, mid-vol, sharpe=2.56
- worst_cell: pfe_sensitivity=0.8, leverage_cap=0.3, ETH/USDT, high-vol, sharpe=0.12

## Standard validators (Step 7) — primary config

`trend_window=40, pfe_period=10, pfe_smoothing=5, base_exposure=0.15, pfe_sensitivity=0.6, leverage_cap=0.3, deadband=0.10`

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction | Param sens rel-std |
|---|---|---|---|---|---|
| BTC/USDT | 1.481 (pass) | 0.1090 (pass) | 0.820 (pass) | 1.0 (pass) | 0.031 (pass) |
| ETH/USDT | 1.210 (pass) | 0.1289 (pass) | 0.795 (pass) | 1.0 (pass) | 0.027 (pass) |

Walk-forward used a manual 4-fold range split (same semantics as
`validators.check_walk_forward`) because `vectorbt.utils.splitting.RangeSplitter`
is unavailable in this environment's installed vectorbt version.

## Decision (Step 8)

**Accepted (crypto only, this sub-iteration)** — BTC/USDT and ETH/USDT
both pass all 5 validators at leverage_cap=0.3, rescuing the prior
2026-09-14-102 crypto MDD rejection. Combined with the existing
2026-09-14-102 QQQ+SPY equity accept, PFE's continuous-sizing dial now
covers the full universe (QQQ, SPY, BTC/USDT, ETH/USDT).
