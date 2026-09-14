# Standard Error Bands (SEB) %B Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-147
**File:** `strategies/2026-09-14_seb_pctb_sizing_sma_trend.py`

## Hypothesis

Standard Error Bands (SEB, Jon Andersen, TASC Sep 1996): a linear-regression
scatter envelope — Basis = SMA(3, LinRegEndpoint(close, 21)), Upper/Lower =
Basis ± K × SmoothedStandardError. Distinct from Bollinger (std-dev around
an SMA) and from this cron trigger's STARC entry (ATR around an SMA).
Confirmed via Google AI-overview synthesis of TASC/LuxAlgo/Commodity.com
(`browser_exec`).

This repo has 3 prior SEB entries (band-breakout rejected, pullback-to-
centerline rejected, band-touch-reversal mean-reversion accepted QQQ-only
but decisively fails crypto). None used SEB as a CONTINUOUS SIZING dial.
This iteration reframes SEB the same way STARC (2026-09-14-144) was:
`seb_pctb = (close - lower) / (upper - lower)`, rescaled to [-1,+1], used as
a sizing multiplier within an SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={seb_k: [1.5,2.0,2.5], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 79, **pass_fraction:** 0.549
- **by_asset_class:** equity 29/72 (0.403), crypto 50/72 (0.694) — notably
  crypto-favorable, the reverse of most sizing-dial strategies this cron
  trigger (which usually lean equity-favorable).
- **by_vol_regime:** low 44/48 (0.917), mid 24/48 (0.5), high 11/48 (0.229).
- **best_cell:** ETH/USDT, seb_k=2.0/deadband=0.25/leverage_cap=1.0,
  mid-vol, Sharpe 2.81.
- **worst_cell:** ETH/USDT, seb_k=1.5/deadband=0.15/leverage_cap=0.4,
  high-vol, Sharpe -0.17.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | k=2.5, db=0.15, lc=0.4 | **0.992 (FAIL, near-miss)** | pass | **FAIL** | pass | pass | **rejected** |
| SPY | k=1.5, db=0.25, lc=1.0 | 1.131 (pass) | pass | **FAIL (net Sharpe ~0.003, 448 trades)** | pass | pass | **rejected** |
| BTC/USDT | k=1.5, db=0.15, lc=0.4 | 1.442 (pass) | pass | pass | pass | pass | **accepted** |
| ETH/USDT | k=2.5, db=0.25, lc=0.4 | 1.244 (pass) | pass | pass | pass | pass | **accepted** |

## Decision

**Accepted:** BTC/USDT, ETH/USDT (all 5 validators pass at leverage_cap=0.4).
**Rejected:** QQQ (near-miss Sharpe 0.992 + decisive TC-survival fail);
SPY (Sharpe passes but decisive TC-survival fail, 448 trades / net Sharpe
~0.003 — high turnover from the tighter regression-based bands generating
excessive crossings on equity, unlike crypto's higher-vol regime where the
same bands are wider in absolute terms and generate fewer signal flips).

**Notable finding:** first sizing-dial strategy this cron trigger where
crypto clearly outperforms equity on both the grid pass_fraction (0.694 vs
0.403) and the final accept/reject outcome (crypto accepted both, equity
rejected both) — a genuinely inverted asset-class pattern worth flagging for
future SEB-family follow-ups (e.g. tune deadband wider specifically for
equity to cut the trade count).

Full raw grid: `grid_result_seb_pctb_sizing.json`. Full raw validators:
`validators_seb_pctb_sizing.json`.
