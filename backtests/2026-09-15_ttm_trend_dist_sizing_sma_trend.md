# Backtest Report: TTM Trend Distance Continuous Sizing Dial (SMA Trend Gate)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_ttm_trend_dist_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-039

## Hypothesis

TTM Trend (John Carter) classifies trend direction by comparing close to a
rolling SMA of hl2 ("average price") over a short window. Per VectorTA's
docs (https://vectoralpha.dev/projects/ta/indicators/ttm_trend/, visited
this iteration), the canonical construction is boolean: `close > SMA(hl2,
period)`. This repo's prior TTM Trend entries (2026-09-10-080 accepted
SPY-only discrete color-flip; 2026-09-10-091 rejected vol-gated variant)
used it as a binary trigger. This iteration instead uses the *normalized
distance* `(close - SMA(hl2, period)) / SMA(hl2, period)`, rolling
z-scored and tanh-squashed into [-1,+1], as a continuous exposure-sizing
dial inside an SMA(trend_window) uptrend gate, with a deadband to cut
turnover -- following this cron trigger's established "continuous sizing
dial" rescue pattern for indicator families previously tested only as
discrete triggers.

## Step 6 — Grid summary (ttm_period x sensitivity, 2 asset classes x 3 vol terciles)

- Grid: `ttm_period in [5, 8, 14]`, `sensitivity in [0.5, 0.8]`, symbols
  `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`.
- **72 cells, 37 passed (pass_fraction = 0.514)**.
- By asset class: equity 19/36, crypto 18/36 — roughly even split, no
  decisive asset-class exclusion.
- By vol regime: low 23/24, mid 12/24, **high 2/24** — like most entries in
  this repo, the edge is concentrated in low/mid volatility regimes and
  collapses in high-vol regimes.
- Best cell: QQQ, ttm_period=5, sensitivity=0.8, low-vol regime, Sharpe 2.83.
- Worst cell: ETH/USDT, ttm_period=5, sensitivity=0.8, high-vol regime,
  Sharpe -0.13.

## Step 7 — Single-config validator suite

Primary config tuned via manual deadband/period sweep to reduce turnover
(`ttm_period=8, sensitivity=0.8, trend_window=40, zscore_window=100,
base_exposure=0.4, leverage_cap=1.0, deadband=0.5`), full sample
2019-01-01 to 2026-09-01:

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass | Param sensitivity (rel std) | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 0.937 (fail, <1.0) | 0.223 (pass) | 0.483 (fail, <0.5) | 0.75 (pass) | 0.182 (pass) | **No** |
| SPY | 1.009 (pass) | 0.146 (pass) | 0.405 (fail, <0.5) | 1.00 (pass) | 0.097 (pass) | **No** |
| BTC/USDT | 1.121 (pass) | 0.552 (fail, <0.25) | 0.976 (pass) | 0.75 (pass) | 0.081 (pass) | **No** |
| ETH/USDT | 0.966 (fail) | 0.572 (fail) | 0.871 (pass) | 1.00 (pass) | 0.132 (pass) | **No** |

No symbol passes all 5 validators. SPY is the closest near-miss (fails
only transaction-cost survival, 0.405 vs 0.5 threshold, by a moderate
margin — deadband sweep up to 0.8 raised net Sharpe toward ~0.46-0.51 but
traded off gross Sharpe below 1.0 in most of those configs). Crypto fails
decisively on max-drawdown regardless of tuning (0.55+ vs 0.25 threshold)
— consistent with most continuous-sizing-dial strategies in this repo
needing an explicit leverage cap well below 1.0 for crypto, which was not
separately retuned this iteration due to time budget.

## Step 8 — Decision: **REJECT**

No asset/config combination passes the full validator suite. Best
candidate (SPY, ttm_period=8/deadband=0.5) is a near-miss on transaction
cost survival only; a future iteration could retune with a
per-symbol-retuned deadband (this repo's established pattern) specifically
targeting SPY, or add a leverage cap < 1.0 for crypto to address the MDD
failure separately.

Walk-forward used the repo's established manual 4-equal-slice fallback
(`vbt.utils.splitting` unavailable in the installed vectorbt version).
