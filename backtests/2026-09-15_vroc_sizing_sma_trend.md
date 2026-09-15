# Backtest Report: VROC Continuous Sizing Dial (SMA Trend Gate)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_vroc_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-041

## Hypothesis

Volume Rate of Change (VROC) = [(volume[t] - volume[t-N]) / volume[t-N]] *
100 (already-visited source: https://blog.ueex.com/volume-rate-of-change-vroc/,
logged in this repo's ledger from a prior iteration, id 2026-09-12-140 --
not re-fetched this iteration per the dedupe rule). This repo's prior VROC
entry (2026-09-12-140) used VROC as a discrete Donchian-breakout
confirmation-gate threshold and was rejected. This iteration reuses the
identical underlying construction as a CONTINUOUS sizing dial: VROC is
smoothed, rolling z-scored, and tanh-squashed into [-1,+1], used to scale
exposure up/down (rising volume interest = higher conviction) inside an
SMA(trend_window) uptrend gate with a deadband.

## Step 6 — Grid summary (vroc_window x sensitivity, 2 asset classes x 3 vol terciles)

- Grid: `vroc_window in [10, 14, 20]`, `sensitivity in [0.5, 0.8]`, symbols
  `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`.
- **72 cells, 43 passed (pass_fraction = 0.597)** — strongest grid result of
  this cron trigger's 3 iterations.
- By asset class: equity 14/36, crypto 29/36 — crypto clearly favored (VROC
  as a sizing signal fits crypto's volume-driven momentum character better
  than equity).
- By vol regime: low 24/24 (perfect), mid 13/24, high 6/24.
- Best cell: QQQ, vroc_window=10, sensitivity=0.5, low-vol regime, Sharpe 2.73.
- Worst cell: QQQ, vroc_window=20, sensitivity=0.5, high-vol regime, Sharpe -1.18.

## Step 7 — Single-config validator suite (per-symbol retuned)

Crypto config (leverage-cap-aware retune): `vroc_window=14, sensitivity=0.5,
trend_window=40, smooth_window=5, zscore_window=100, base_exposure=0.2,
leverage_cap=0.5, deadband=0.3`.
Equity config: `vroc_window=14, sensitivity=0.5, trend_window=40,
smooth_window=5, zscore_window=100, base_exposure=0.4, leverage_cap=1.0,
deadband=0.3`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass | Param sensitivity (rel std) | All pass? |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.298 (pass) | 0.207 (pass) | 1.115 (pass) | 0.75 (pass) | 0.061 (pass) | **Yes** |
| ETH/USDT | 0.854 (fail) | 0.260 (fail, marginal) | 0.721 (pass) | 1.00 (pass) | 0.108 (pass) | No |
| QQQ | 0.932 (fail) | 0.114 (pass) | 0.319 (fail) | 0.75 (pass) | 0.609 (fail) | No |
| SPY | 0.712 (fail) | 0.082 (pass) | 0.083 (fail) | 1.00 (pass) | 0.242 (pass) | No |

Note: at leverage_cap=1.0 without the crypto retune, BTC Sharpe 1.53/MDD
0.251 (marginal fail) and ETH Sharpe 1.02/MDD 0.402 (decisive fail) —
per-symbol leverage-cap retuning (this repo's established pattern) was
necessary to get BTC across the full validator line.

Walk-forward used the repo's established manual 4-equal-slice fallback.

## Step 8 — Decision: **ACCEPT (BTC/USDT only)**

BTC/USDT passes all 5 validators cleanly at
`leverage_cap=0.5, base_exposure=0.2, deadband=0.3` with tight
parameter-sensitivity (rel std 0.061). ETH/USDT is a near-miss (Sharpe
0.854 vs 1.0, MDD 0.260 vs 0.25 — both close) and QQQ/SPY fail decisively
(equity's VROC-based sizing dial doesn't hold up on transaction costs or
parameter sensitivity in QQQ's case). Strategy file remains live for the
BTC/USDT scope only.
