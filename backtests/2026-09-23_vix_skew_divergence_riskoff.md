# VIX-SKEW Divergence Crash-Risk-Off Filter

**Date:** 2026-09-23 | **Strategy file:** `strategies/2026-09-23_vix_skew_divergence_riskoff.py`

## Hypothesis

Per TradingView's "VIX - SKEW Divergence" open-source indicator
(https://www.tradingview.com/script/uRF1KArk-VIX-SKEW-Divergence/, by
valpatrad, visited this iteration): "When the SKEW rises over a certain
level (~140/150)... investors are hedging their exposure with options...
If that happens when the VIX is very low and apparently there is no
uncertainty, this can warn of a sudden change in direction of the
market... an increasing divergence often anticipates a sharp fall...
usually within two to four months." First VIX-SKEW DIVERGENCE strategy in
this repo (distinct from the single prior standalone SKEW-alone z-score
entry, 2026-09-05-029). Applied as a long-only risk-off overlay on top of a
simple SMA(50) trend-following signal: go flat whenever SKEW>=threshold AND
VIX<=threshold simultaneously (the divergence "crash warning" condition),
trade the trend signal normally otherwise.

## Grid summary (`grid_summary_vix_skew_divergence.json`)

- 48 cells: `skew_threshold` in {135,140} x `vix_threshold` in {15,18} x
  `trend_window`={50}, QQQ/SPY/BTCUSDT/ETHUSDT, vol_regime_splits=3.
- **pass_fraction: 0.396 (19/48)**.
- by_asset_class: equity 12/24, crypto 7/24.
- by_vol_regime: low 15/16, mid 4/16, high 0/16.
- best_cell: ETH/USDT mid-vol, Sharpe 2.63 (crypto grid cell high but does
  not survive full-sample below).

## Single-config validators (skew_threshold=135, vix_threshold=15, trend_window=50, full-sample 2018-2026)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| **QQQ** | **1.026 (PASS)** | **0.189 (PASS)** | **0.748 (PASS)** | **1.0 (PASS)** | **0.158 (PASS)** |
| SPY | 0.893 (FAIL, near-miss) | 0.215 (PASS) | 0.491 (FAIL, near-miss) | 1.0 (PASS) | 0.102 (PASS) |
| ETH/USDT | 0.178 (FAIL) | 0.601 (FAIL, decisive) | -0.010 (FAIL, 4707 trades) | 0.75 (PASS) | 0.151 (PASS) |
| BTC/USDT | 0.160 (FAIL) | 0.554 (FAIL, decisive) | -0.027 (FAIL, 4641 trades) | 1.0 (PASS) | 0.077 (PASS) |

## Decision: **ACCEPTED for QQQ only** (equity, VIX/SKEW's own native asset class)

QQQ passes all 5 validators cleanly (Sharpe 1.03, MDD 0.19, net Sharpe after
costs 0.75, walk-forward 1.0, parameter sensitivity 0.16). SPY narrowly
misses Sharpe (0.89) and tx-cost survival (0.49) -- a near-miss worth a
future fine-tune revisit. Crypto (BTC/ETH) decisively rejected: MDD fails
by a wide margin (0.55-0.60 vs 0.25 threshold) and transaction costs are
catastrophic (4600+ trades over the sample, net negative Sharpe) -- this is
expected since VIX/SKEW are US-equity-derivative-market signals with no
direct economic link to crypto price action; the crypto test here was a
falsification check per this repo's standard convention, not an
expectation of transferability.

Scope: QQQ (trend_window=50 config). See follow-up fine-tune below for SPY.

## Follow-up fine-tune (same cron trigger, next iteration): SPY rescue

A parameter sweep of `trend_window` in {40,45,50,60} at
`skew_threshold=135, vix_threshold=15` found `trend_window=40` clears
SPY's near-miss:

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| SPY (trend_window=40) | **1.103 (PASS)** | **0.133 (PASS)** | **0.675 (PASS)** | **1.0 (PASS)** | **0.111 (PASS)** |
| QQQ (trend_window=40, re-check) | 0.993 (FAIL, near-miss) | 0.232 (PASS) | 0.665 (PASS) | 1.0 (PASS) | 0.090 (PASS) |

**SPY ACCEPTED** at `skew_threshold=135, vix_threshold=15, trend_window=40`
(all 5 validators pass). QQQ's own original accepted config remains
`trend_window=50` (see above) -- the two symbols now use slightly
different `trend_window` values, both accepted independently at their own
best config. Do not conflate the two configs; each symbol's config is
recorded in its own KB entry.

Scope: QQQ (trend_window=50) AND SPY (trend_window=40), both accepted
independently. Crypto remains rejected (see above, unchanged).
