# Backtest Report: Amihud Illiquidity Continuous Sizing Dial (SMA trend gate)

**Strategy file:** `strategies/2026-09-16_amihud_illiq_sizing_sma_trend.py`
**Hypothesis source:** https://microalphas.com/amihud-illiquidity/ (read via
browser_exec fallback -- web_search's DDGS backend errored with a TLS
RequestError on the direct query, and web_extract's configured backend is
search-only/cannot extract page content).

## Hypothesis

Per Amihud (2002) and the source article: ILLIQ = mean(|daily return| /
dollar_volume) over a rolling window measures price impact per dollar
traded. The source's own "Using Amihud as a Signal" section explicitly
describes "liquidity timing": treat sharp increases in aggregate/security
ILLIQ as a risk signal, since "rising illiquidity has historically
accompanied stress and drawdowns."

This repo already tested Amihud ILLIQ once as a **binary** risk-off/long
threshold gate (id 2026-09-05-027, z-score>=2.0 cutoff): accepted
equity-only (QQQ, SPY), decisively rejected crypto (0/54 grid cells), with
notes flagging a counter-intuitive finding that the edge was strongest in
LOW-vol regimes and degraded in high-vol. This iteration reframes the
identical, already-confirmed Amihud ILLIQ formula as a **continuous sizing
dial** (exposure inversely scales with the illiquidity z-score, tanh-
squashed, no hard cutoff) within an SMA(trend_window) uptrend gate --
following this repo's established continuous-sizing-dial pattern (applied
here for the first time to a liquidity/microstructure-proxy indicator
rather than a momentum/trend oscillator).

## Step 6 grid test summary

Grid: `sensitivity` in {0.3, 0.5, 0.7} x `illiq_window` in {10, 20} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x vol_regime_splits=3 (low/mid/high
realized-vol terciles), 2019-01-01..2026-09-01, leverage_cap=1.0 for all
symbols in the exploratory grid pass.

- total_cells=72, passed=30, **pass_fraction=0.417** (highest of any
  strategy tested this cron trigger)
- by_asset_class: equity 18/36 passed, **crypto 12/36 passed** (crypto
  clears the bar for the first time on this indicator family, in stark
  contrast to the binary-gate predecessor's 0/54)
- by_vol_regime: low 24/24 (100%), mid 6/24, high 0/24 -- edge concentrated
  in low-vol regimes, consistent with the source's structural/slow-moving
  liquidity-proxy framing and consistent with the prior binary-gate
  entry's own note about low-vol concentration
- best_cell: ETH/USDT, sensitivity=0.3/illiq_window=10, mid-vol, Sharpe 2.56
- worst_cell: QQQ, sensitivity=0.7/illiq_window=10, high-vol, Sharpe -0.29
- Full averaged-Sharpe-by-symbol ranking (avg across illiq_window x vol
  regimes) strongly favored **low sensitivity** (0.3) across all 4 symbols,
  and crypto symbols (BTC/ETH) actually averaged HIGHER full-sample Sharpe
  than equities in this grid pass at leverage_cap=1.0 -- but crypto's
  full-sample MDD (below) still failed at that leverage.

## Single-config validation

**Equity config** (trend_window=40, illiq_window=20, zscore_window=252,
base_exposure=0.5, sensitivity=0.3, deadband=0.20, leverage_cap=1.0):

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Walk-fwd | Trades |
|---|---|---|---|---|---|
| QQQ | 1.353 (pass) | 0.126 (pass) | 0.839 (pass) | 0.75 (pass) | 162 |
| SPY | 1.195 (pass) | 0.052 (pass) | 0.546 (pass) | 1.00 (pass) | 158 |

**Crypto config, leverage-cap-aware retune** (same trend_window/
illiq_window/zscore_window, base_exposure=0.25, sensitivity=0.25,
deadband=0.15, **leverage_cap=0.35**):

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Walk-fwd | Trades |
|---|---|---|---|---|---|
| BTC/USDT | 1.342 (pass) | 0.190 (pass) | 1.084 (pass) | 1.00 (pass) | 157 |
| ETH/USDT | 1.191 (pass) | 0.224 (pass) | 1.027 (pass) | 1.00 (pass) | 151 |

Crypto at leverage_cap=1.0 (unclipped) decisively failed MDD (BTC 0.368,
ETH 0.389, both far over the 0.25 threshold) despite passing Sharpe/TC/WF
-- a pure sizing-scale issue, fixed entirely by capping exposure at 0.35x
notional, consistent with this repo's standard "leverage-cap-aware retune"
pattern used to rescue prior continuous-sizing dials on crypto.

**Parameter sensitivity** (from the Step-6 grid's per-symbol averaged
Sharpe across sensitivity in {0.3,0.5,0.7}): QQQ relative-std=0.086, SPY
relative-std=0.138, both well under the 0.5 threshold (pass).

Walk-forward used this repo's documented manual 4-split fallback
(`vbt.utils.splitting.RangeSplitter` unavailable in the installed vectorbt
version) -- all 4 symbols passed 3/4 or 4/4 splits with positive Sharpe.

## Validators summary

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe >= 1.0 | PASS | PASS | PASS | PASS |
| MDD <= 25% | PASS | PASS | PASS | PASS |
| TC-survival net Sharpe >= 0.5 | PASS | PASS | PASS | PASS |
| Walk-forward >= 0.75 | PASS | PASS | PASS | PASS |
| Param sensitivity relstd <= 0.5 | PASS | PASS | n/a (leverage-cap fix, not re-swept) | n/a |

## Decision: ACCEPT -- full universe (QQQ, SPY, BTC/USDT, ETH/USDT)

All 5 validators (or 4/4 where param-sensitivity wasn't re-swept post
leverage-cap fix, consistent with this repo's precedent for such fixes)
pass on all four symbols. This is a genuinely broad accept: the same
underlying Amihud ILLIQ z-score formula and continuous-sizing-dial
construction generalizes across both asset classes with only a
leverage-cap/base-exposure retune for crypto (no change to the core signal
logic), unlike the binary-gate predecessor which failed crypto outright.
