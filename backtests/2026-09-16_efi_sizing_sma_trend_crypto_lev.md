# Backtest Report: EFI Sizing Dial — Crypto Leverage-Cap Recalibration

**Strategy file:** `strategies/2026-09-16_efi_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16
**Hypothesis source:** Formula unchanged from 2026-09-14-105 (Elder Force
Index, Alexander Elder; DuckDuckGo HTML SERP arrowalgo.com/ta-lib.org/
positioned.app/chart-formations.com/lightningchart.com). This
sub-iteration reuses the confirmed formula and applies this repo's
leverage-cap-aware crypto retune pattern.

## Hypothesis

2026-09-14-105's EFI z-score/tanh continuous sizing dial, gated by an
`SMA(trend_window)` uptrend filter, was accepted decisively on equity
(QQQ+SPY) but rejected on crypto: BTC/USDT MDD 39.92% > 25% threshold
with leverage_cap left at the equity default 1.0. Cutting `leverage_cap`
to 0.3 (scaling `base_exposure`/`deadband` proportionally) should keep
crypto MDD under 25% while retaining the dial's strong crypto Sharpe.

## Grid test (Step 6)

`param_grid={"efi_sensitivity": [0.4, 0.6, 0.8], "leverage_cap": [0.25, 0.3, 0.35]}`,
`symbols={"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- total_cells=54, passed=45, **pass_fraction=0.833**
- by_asset_class: crypto 45/54
- by_vol_regime: low 18/18, mid 18/18, high 9/18
- best_cell: efi_sensitivity=0.6, leverage_cap=0.3, ETH/USDT, mid-vol, sharpe=2.41
- worst_cell: efi_sensitivity=0.8, leverage_cap=0.25, ETH/USDT, high-vol, sharpe=0.21

## Standard validators (Step 7) — primary config

`trend_window=40, efi_ema_span=13, efi_zscore_window=100, base_exposure=0.15, efi_sensitivity=0.6, leverage_cap=0.3, deadband=0.10`

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction | Param sens rel-std |
|---|---|---|---|---|---|
| BTC/USDT | 1.267 (pass) | 0.1638 (pass) | 0.656 (pass) | 1.0 (pass) | 0.046 (pass) |
| ETH/USDT | 1.212 (pass) | 0.1336 (pass) | 0.815 (pass) | 1.0 (pass) | 0.042 (pass) |

Walk-forward used a manual 4-fold range split (same semantics as
`validators.check_walk_forward`) because `vectorbt.utils.splitting.RangeSplitter`
is unavailable in this environment's installed vectorbt version.

## Decision (Step 8)

**Accepted (crypto only, this sub-iteration)** — BTC/USDT and ETH/USDT
both pass all 5 validators at leverage_cap=0.3, rescuing the prior
2026-09-14-105 crypto MDD rejection. Combined with the existing
2026-09-14-105 QQQ+SPY equity accept, EFI's continuous-sizing dial now
covers the full universe (QQQ, SPY, BTC/USDT, ETH/USDT).
