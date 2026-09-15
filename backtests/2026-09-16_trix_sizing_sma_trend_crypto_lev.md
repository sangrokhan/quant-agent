# Backtest Report: TRIX Sizing Dial — Crypto Leverage-Cap Recalibration

**Strategy file:** `strategies/2026-09-16_trix_sizing_sma_trend_crypto_lev.py`
**Date:** 2026-09-16
**Hypothesis source:** Formula unchanged from 2026-09-14-114 (TRIX;
Investopedia/TrendSpider/AvaTrade via Google AI overview, browser_exec).
This sub-iteration reuses the confirmed formula and applies this repo's
leverage-cap-aware crypto retune pattern.

## Hypothesis

2026-09-14-114's TRIX z-score/tanh continuous sizing dial, gated by an
`SMA(trend_window)` uptrend filter, was accepted decisively on equity
(QQQ+SPY, very low param-sensitivity) but rejected on crypto: BTC/USDT
MDD 40.1% > 25% threshold at the equity-tuned config (leverage_cap=1.0,
sensitivity=0.6, deadband=0.2). Cutting `leverage_cap` and using a lower
`trix_sensitivity` (0.25/0.4 respectively, found via a small sweep since
the equity-default sensitivity=0.6 left ETH/USDT Sharpe just under 1.0 at
leverage_cap=0.3) rescues both symbols.

## Grid test (Step 6)

`param_grid={"trix_sensitivity": [0.4, 0.6, 0.8], "leverage_cap": [0.25, 0.3, 0.35]}`,
`symbols={"crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- total_cells=54, passed=37, **pass_fraction=0.685** (lower than most
  other sizing-dial retunes this cron trigger, reflecting TRIX's weaker
  crypto low-vol-regime performance: low-vol only 10/18 pass)
- by_asset_class: crypto 37/54
- by_vol_regime: low 10/18, mid 18/18, high 9/18
- best_cell: trix_sensitivity=0.4, leverage_cap=0.25, ETH/USDT, mid-vol, sharpe=2.22
- worst_cell: trix_sensitivity=0.4, leverage_cap=0.25, ETH/USDT, high-vol, sharpe=0.32

## Standard validators (Step 7) — primary config

`trend_window=40, trix_span=14, trix_zscore_window=100, base_exposure=0.15, trix_sensitivity=0.4, leverage_cap=0.25, deadband=0.10`

(An initial attempt at trix_sensitivity=0.6/leverage_cap=0.3 left ETH/USDT
Sharpe at 0.985, a near-miss below the 1.0 threshold; lowering sensitivity
to 0.4 and leverage_cap to 0.25 fixed this.)

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction | Param sens rel-std |
|---|---|---|---|---|---|
| BTC/USDT | 1.211 (pass) | 0.1169 (pass) | 0.817 (pass) | 0.75 (pass) | 0.023 (pass) |
| ETH/USDT | 1.050 (pass) | 0.1142 (pass) | 0.744 (pass) | 1.0 (pass) | 0.062 (pass) |

Walk-forward used a manual 4-fold range split (same semantics as
`validators.check_walk_forward`) because `vectorbt.utils.splitting.RangeSplitter`
is unavailable in this environment's installed vectorbt version. BTC/USDT's
walk-forward pass_fraction of 0.75 is at the exact threshold (one of 4
folds had non-positive Sharpe) — a thinner margin than most other retunes
this cron trigger, worth monitoring in a future revisit.

## Decision (Step 8)

**Accepted (crypto only, this sub-iteration)** — BTC/USDT and ETH/USDT
both pass all 5 validators at trix_sensitivity=0.4/leverage_cap=0.25,
rescuing the prior 2026-09-14-114 crypto MDD rejection, though with a
thinner margin (lower grid pass_fraction, walk-forward exactly at
threshold for BTC/USDT) than most other retunes this cron trigger. Combined
with the existing 2026-09-14-114 QQQ+SPY equity accept, TRIX's
continuous-sizing dial now covers the full universe (QQQ, SPY, BTC/USDT,
ETH/USDT), noted as a narrower-margin accept for future monitoring.
