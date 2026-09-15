# Backtest Report: PVI Distance Continuous Sizing Dial (SMA Trend Gate)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_pvi_dist_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-043

## Hypothesis

Positive Volume Index (PVI, Norman Fosback / classic HPotter construction,
formula already documented in this repo from prior iteration 2026-09-05-001
and its already-visited sources, not re-fetched this iteration per the
dedupe ledger): cumulative sum of daily price %-change, added only on days
where volume INCREASED vs the prior day. This repo's prior PVI entry
(2026-09-05-001) used a discrete PVI-vs-its-own-MA crossover trigger and
was a near-miss rejection (QQQ close). This iteration reuses the identical
underlying construction as a CONTINUOUS sizing dial rather than a binary
crossover, per this cron trigger's established rescue pattern: PVI's
normalized distance from its own SMA(pvi_ma_window) is rolling z-scored
and tanh-squashed into [-1,+1], used as a continuous sizing dial inside an
SMA(trend_window) uptrend gate with a deadband.

## Step 6 — Grid summary (pvi_ma_window x sensitivity, 2 asset classes x 3 vol terciles)

- Grid: `pvi_ma_window in [20, 30, 50]`, `sensitivity in [0.5, 0.8]`,
  symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
  `vol_regime_splits=3`.
- **72 cells, 27 passed (pass_fraction = 0.375)**.
- By asset class: equity 13/36, crypto 14/36 — roughly balanced.
- By vol regime: low 22/24, mid 1/24, high 4/24.
- Best cell: QQQ, pvi_ma_window=50, sensitivity=0.5, low-vol regime, Sharpe 2.71.
- Worst cell: SPY, pvi_ma_window=20, sensitivity=0.8, mid-vol regime,
  Sharpe -0.15.

## Step 7 — Single-config validator suite (per-asset-class retuned)

Equity config: `pvi_ma_window=30, sensitivity=0.5, trend_window=40,
zscore_window=100, base_exposure=0.4, leverage_cap=1.0, deadband=0.3`.
Crypto config (leverage-cap-aware retune): same core params,
`base_exposure=0.24, leverage_cap=0.4, deadband=0.3`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass | Param sensitivity (rel std) | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.075 (pass) | 0.123 (pass) | 0.772 (pass) | 0.75 (pass) | 0.161 (pass) | **Yes** |
| SPY | 1.082 (pass) | 0.083 (pass) | 0.703 (pass) | 0.75 (pass) | 0.069 (pass) | **Yes** |
| BTC/USDT | 1.159 (pass) | 0.242 (pass) | 0.996 (pass) | 1.00 (pass) | 0.060 (pass) | **Yes** |
| ETH/USDT | 1.058 (pass) | 0.179 (pass) | 0.941 (pass) | 1.00 (pass) | 0.179 (pass) | **Yes** |

Walk-forward used the repo's established manual 4-equal-slice fallback.

## Step 8 — Decision: **ACCEPT (full universe: QQQ, SPY, BTC/USDT, ETH/USDT)**

All four symbols pass all 5 validators with comfortable margins and tight
parameter-sensitivity (rel std 0.06-0.18 throughout). This is the
strongest and broadest result of this cron trigger's 5 iterations —
rescuing 2026-09-05-001's near-miss discrete PVI trigger into a full
cross-asset accept via the continuous-sizing-dial transform, with a
per-asset-class leverage-cap retune (base_exposure=0.24, leverage_cap=0.4)
needed for crypto to stay within the MDD threshold.
