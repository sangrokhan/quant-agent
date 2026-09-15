# Backtest Report: Elder-Ray Net Power Sizing Dial — Crypto Leverage-Cap Recalibration

**Strategy file:** `strategies/2026-09-16_elderray_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16
**Hypothesis source:** Formula unchanged from 2026-09-14-121 (Dr.
Alexander Elder, 1989; investopedia.com/terms/e/elderray.asp, read via
browser_exec). This sub-iteration reuses the confirmed formula and applies
this repo's leverage-cap-aware crypto retune pattern.

## Hypothesis

2026-09-14-121's Elder-Ray ATR-normalized net-power continuous sizing
dial, gated by an `SMA(trend_window)` uptrend filter, was accepted
decisively on equity (QQQ+SPY, first Elder-Ray accept after 8 prior
binary-trigger rejections) but rejected on crypto with an MDD-only miss:
BTC/USDT MDD 37.7% > 25% threshold, with Sharpe 1.497 (pass), TC-survival
0.871 (pass), walk-forward 1.0 (pass), param-sensitivity 0.014 (pass) --
all other 4 validators already passing. Cutting `leverage_cap` to 0.3
(scaling `base_exposure` proportionally) should pull crypto MDD under
25%. An initial attempt at deadband=0.05 caused BTC/USDT's TC-survival to
fail (484 trades, net Sharpe 0.425 < 0.5) due to elevated turnover;
widening deadband to 0.10 fixed this while keeping all other validators
passing.

## Grid test (Step 6)

`param_grid={"sensitivity": [0.3, 0.5, 0.7], "leverage_cap": [0.25, 0.3, 0.35]}`,
`symbols={"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01 (grid run at deadband=0.05 as the code default at
grid-test time; primary config below uses the corrected deadband=0.10):

- total_cells=54, passed=45, **pass_fraction=0.833**
- by_asset_class: crypto 45/54
- by_vol_regime: low 18/18, mid 18/18, high 9/18
- best_cell: sensitivity=0.7, leverage_cap=0.35, ETH/USDT, mid-vol, sharpe=2.67
- worst_cell: sensitivity=0.7, leverage_cap=0.35, ETH/USDT, high-vol, sharpe=0.30

## Standard validators (Step 7) — primary config

`trend_window=40, ema_window=13, atr_window=14, net_power_reference=2.0, base_exposure=0.15, sensitivity=0.5, leverage_cap=0.3, deadband=0.10`

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction | Param sens rel-std |
|---|---|---|---|---|---|
| BTC/USDT | 1.484 (pass) | 0.1394 (pass) | 0.956 (pass) | 1.0 (pass) | 0.023 (pass) |
| ETH/USDT | 1.233 (pass) | 0.1537 (pass) | 0.913 (pass) | 1.0 (pass) | 0.022 (pass) |

Walk-forward used a manual 4-fold range split (same semantics as
`validators.check_walk_forward`) because `vectorbt.utils.splitting.RangeSplitter`
is unavailable in this environment's installed vectorbt version.

## Decision (Step 8)

**Accepted (crypto only, this sub-iteration)** — BTC/USDT and ETH/USDT
both pass all 5 validators at leverage_cap=0.3, deadband=0.10, rescuing
the prior 2026-09-14-121 crypto MDD rejection. Combined with the existing
2026-09-14-121 QQQ+SPY equity accept, Elder-Ray's continuous-sizing dial
now covers the full universe (QQQ, SPY, BTC/USDT, ETH/USDT).
