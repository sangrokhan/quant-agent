# Backtest Report: Kaufman Efficiency Ratio Sizing Dial — Crypto Leverage-Cap Recalibration

**Strategy file:** `strategies/2026-09-16_er_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16
**Hypothesis source:** Formula unchanged from 2026-09-14-111 (Kaufman
Efficiency Ratio, Perry Kaufman, KAMA component; Google AI overview via
browser_exec). This sub-iteration reuses the confirmed formula and applies
this repo's leverage-cap-aware crypto retune pattern.

## Hypothesis

2026-09-14-111's ER (natively bounded [0,1]) continuous sizing dial,
gated by an `SMA(trend_window)` uptrend filter, was accepted decisively on
equity (QQQ+SPY) but decisively rejected on crypto: BTC/USDT MDD 32.9% >
25% threshold, 0/108 grid cells passing, with leverage_cap left at the
equity default 1.0. This is the same "trend-efficiency family" as VHF/PFE/
RWI-diff/CHOP that had generalized to crypto only after leverage-cap
retuning in prior sub-iterations this cron trigger. Cutting `leverage_cap`
to 0.3 (scaling `base_exposure`/`deadband` proportionally) should pull
crypto MDD under 25%.

## Grid test (Step 6)

`param_grid={"er_sensitivity": [0.5, 0.7, 0.9], "leverage_cap": [0.25, 0.3, 0.35]}`,
`symbols={"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- total_cells=54, passed=45, **pass_fraction=0.833**
- by_asset_class: crypto 45/54
- by_vol_regime: low 18/18, mid 18/18, high 9/18
- best_cell: er_sensitivity=0.5, leverage_cap=0.25, ETH/USDT, mid-vol, sharpe=2.43
- worst_cell: er_sensitivity=0.9, leverage_cap=0.25, ETH/USDT, high-vol, sharpe=0.24

## Standard validators (Step 7) — primary config

`trend_window=40, er_window=10, base_exposure=0.1, er_sensitivity=0.7, leverage_cap=0.3, deadband=0.08`

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction | Param sens rel-std |
|---|---|---|---|---|---|
| BTC/USDT | 1.493 (pass) | 0.1037 (pass) | 0.631 (pass) | 1.0 (pass) | 0.023 (pass) |
| ETH/USDT | 1.252 (pass) | 0.1202 (pass) | 0.700 (pass) | 1.0 (pass) | 0.038 (pass) |

Walk-forward used a manual 4-fold range split (same semantics as
`validators.check_walk_forward`) because `vectorbt.utils.splitting.RangeSplitter`
is unavailable in this environment's installed vectorbt version.

## Decision (Step 8)

**Accepted (crypto only, this sub-iteration)** — BTC/USDT and ETH/USDT
both pass all 5 validators at leverage_cap=0.3, rescuing the prior
2026-09-14-111 crypto MDD rejection and confirming that the
trend-efficiency family (VHF/PFE/RWI-diff/CHOP/ER) generalizes to crypto
once leverage-cap retuned, resolving the earlier open question raised in
2026-09-14-111's own notes ("breaks the trend-efficiency-family-generalizes
-to-crypto hypothesis" — that conclusion was premature; it just needed a
tighter leverage cap like the family's other members). Combined with the
existing 2026-09-14-111 QQQ+SPY equity accept, ER's continuous-sizing dial
now covers the full universe (QQQ, SPY, BTC/USDT, ETH/USDT).
