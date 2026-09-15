# Backtest Report: RWI Sizing Dial — Crypto Leverage-Cap Recalibration

**Strategy file:** `strategies/2026-09-16_rwi_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16
**Hypothesis source:** Formula unchanged from 2026-09-14-104 (Random Walk
Index, Michael Poulos; confirmed via DuckDuckGo HTML SERP —
linnsoft.com, strike.money, stockmaniacs.net, tradingsim.com). This
sub-iteration reuses the confirmed formula and applies this repo's
established leverage-cap-aware crypto retune pattern (no new external
fetch needed).

## Hypothesis

2026-09-14-104's RWI signed-diff (`tanh(RWI_high - RWI_low)`) continuous
sizing dial, gated by an `SMA(trend_window)` uptrend filter, was accepted
decisively on equity (QQQ+SPY) but rejected on crypto due to BTC/USDT MDD
37.99% > 25% threshold (leverage_cap left at equity default 1.0). Cutting
`leverage_cap` to 0.3 (scaling `base_exposure` and `deadband` down
proportionally) should preserve the dial's shape/edge while keeping crypto
MDD under 25%.

## Grid test (Step 6)

`param_grid={"rwi_sensitivity": [0.5, 0.65, 0.8], "leverage_cap": [0.25, 0.3, 0.35]}`,
`symbols={"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- total_cells=54, passed=45, **pass_fraction=0.833**
- by_asset_class: crypto 45/54
- by_vol_regime: low 18/18, mid 18/18, high 9/18
- best_cell: rwi_sensitivity=0.8, leverage_cap=0.35, ETH/USDT, mid-vol, sharpe=2.50
- worst_cell: rwi_sensitivity=0.8, leverage_cap=0.3, ETH/USDT, high-vol, sharpe=0.44

## Standard validators (Step 7) — primary config

`trend_window=40, rwi_window=14, base_exposure=0.15, rwi_sensitivity=0.65, leverage_cap=0.3, deadband=0.08`

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction | Param sens rel-std |
|---|---|---|---|---|---|
| BTC/USDT | 1.473 (pass) | 0.1436 (pass) | 0.826 (pass) | 1.0 (pass) | 0.018 (pass) |
| ETH/USDT | 1.282 (pass) | 0.1193 (pass) | 0.847 (pass) | 1.0 (pass) | 0.008 (pass) |

Walk-forward used a manual 4-fold range split (each fold Sharpe > 0)
because `vectorbt.utils.splitting.RangeSplitter` is unavailable in this
environment's installed vectorbt version — same pass/fail semantics as
`validators.check_walk_forward`, noted in evidence as a fallback.

## Decision (Step 8)

**Accepted (crypto only, this sub-iteration)** — BTC/USDT and ETH/USDT both
pass all 5 validators at leverage_cap=0.3, rescuing the prior 2026-09-14-104
crypto MDD rejection. Combined with the existing 2026-09-14-104 QQQ+SPY
equity accept, RWI's continuous-sizing dial now covers the full universe
(QQQ, SPY, BTC/USDT, ETH/USDT).
