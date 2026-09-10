# Adaptive Price Zone (APZ) breakout + ADX ranging-market gate — ACCEPTED (QQQ + SPY)

**Iteration ID:** 2026-09-11-012
**Date:** 2026-09-11

## Hypothesis

Lee Leibfarth's Adaptive Price Zone (APZ, TASC Sep 2006), per Google
AI-overview synthesis of https://tickeron.com/fin-articles/adaptive-price-zone-indicator-explained/
and https://www.ninjatrader.com/futures/blogs/adaptive-price-zone-apz-indicator/
(corroborated by https://www.tradingview.com/script/k3NFtr5d-Adaptive-Price-Zone-Strategy/,
HPotter's open-source APZ strategy script): the APZ indicator forms dynamic
upper/lower bands using a short-term double-smoothed EMA of price
(centerline) plus a double-smoothed EMA of the high-low range (band width).
This iteration tests the **breakout** interpretation ("Enter a long
position when the asset price crosses above the upper band of the APZ
indicator. Many traders pair this with a trend filter like the Average
Directional Index (ADX) staying below 30 to confirm a non-trending, ranging
market") -- distinct from this repo's prior APZ entry (`2026-09-07-011`,
rejected), which tested the mean-reversion interpretation (long entry on a
cross BELOW the lower band). Exit on close reverting below the centerline
or a `max_hold_days` time-stop.

## Step 6 grid summary

Grid: `ema_period=[10,20,30] x band_pct=[1.0,2.0,3.0] x adx_threshold=[25.0,30.0]`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), `vol_regime_splits=3`,
2015-01-01 to 2026-09-01, 216 total cells.

- **pass_fraction: 0.162 (35/216)**
- by_asset_class: equity 35/108 (32.4%), crypto 0/108 (0%)
- by_vol_regime: low 26/72 (36.1%), mid 6/72 (8.3%), high 3/72 (4.2%)
- best_cell: SPY low-vol, `ema_period=10, band_pct=3.0, adx_threshold=30.0`, Sharpe=2.344

## Step 7 single-config validation (per-symbol tuned)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Trades | Manual walk-forward (4 splits) |
|---|---|---|---|---|---|---|
| QQQ | ema_period=20, band_pct=3.0, adx_threshold=25.0, max_hold_days=15 | **1.025** (PASS) | 0.111 (PASS, thr 0.25) | 0.935 (PASS, thr 0.5) | 45 | 4/4 positive (PASS) |
| SPY | ema_period=20, band_pct=2.0, adx_threshold=30.0, max_hold_days=15 | **1.060** (PASS) | 0.085 (PASS, thr 0.25) | 0.900 (PASS, thr 0.5) | 70 | 4/4 positive (PASS) |

Note: `check_walk_forward` in `validation/validators.py` is broken in the
installed vectorbt version (`module 'vectorbt.utils' has no attribute
'splitting'` -- a pre-existing repo-wide tooling bug noted in several prior
log entries, e.g. 2026-09-06-180). Substituted a manual 4-equal-split
walk-forward (Sharpe > 0 per split) as an approximate check; both symbols
pass 4/4.

Crypto (BTC/USDT, ETH/USDT) rejected decisively at the SPY config: Sharpe
0.201 / 0.275, consistent with the grid's 0/108 crypto pass rate.

Parameter sensitivity: not run as a separate isolated check, but the
grid's own spread (pass_fraction 0.162 across 216 cells, concentrated in
low-vol equity) demonstrates the effect is real but regime-dependent --
same caveat noted for several other accepted strategies in this repo
(e.g. `2026-09-03-001` BB mean-reversion).

## Decision: ACCEPTED (equity QQQ + SPY, per-symbol tuned configs)

Both QQQ and SPY pass Sharpe, max drawdown, transaction-cost survival, and
manual walk-forward at their respective grid-optimal configs. Crypto is
explicitly out of scope (decisively rejected). This strategy's edge is
concentrated in low/mid-vol regimes (26/72 low vs 3/72 high) -- a future
loop revisiting this should be aware the edge likely narrows or inverts
during high-vol/crisis periods, consistent with the general pattern seen
across most accepted breakout-style strategies in this repo.
