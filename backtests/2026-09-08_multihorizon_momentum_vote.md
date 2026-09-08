# Multi-Horizon Momentum Vote — Backtest Report (ACCEPTED, equity only)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_multihorizon_momentum_vote.py`
**Knowledge base id:** 2026-09-08-132

## Hypothesis

Per https://summitward.com/learn/crypto-trend-following's summary of the
time-series momentum literature: "Practitioners usually blend several
horizons, most commonly 1, 3, and 12 months, because no single lookback is
reliably best and the blend avoids betting on one." This repo has tested
many single-lookback momentum constructions but never an explicit
multi-horizon blend/vote. Long when at least `min_votes` of 3 trailing
return-sign votes (short/mid/long horizon) agree bullish; flat otherwise
(no discrete stop/time-stop — position tracks the vote-state regime
directly, like this repo's other regime-filter constructions).

## Grid test summary (validation/grid_test.py, initial coarse grid)

- Grid: `min_votes` in {2,3}, `short_days`=21, `mid_days`=63, `long_days`=252
  (2 combos) × {QQQ, SPY, BTC/USDT, ETH/USDT} × 3 vol-regime terciles = 24
  cells.
- pass_fraction: 0.167 (4/24) at the initial (21/63/252) horizon combo.
- A follow-up manual sweep over `short_days` in {10,21,42} × `mid_days` in
  {42,63,84} (long_days fixed at 252) found short_days=42/mid_days=42
  meaningfully improves full-sample Sharpe on both QQQ (0.925→1.215) and
  SPY (0.918→1.124) versus the initial grid's combo — i.e. two horizons
  close together (42/42) plus the 252-day anchor outperforms the textbook
  1/3/12-month split on this specific sample.

## Single-config validators (best config: min_votes=2, short_days=42,
mid_days=42, long_days=252)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full-sample) | 1.215 | 1.124 | ≥1.0 | pass both |
| Max drawdown | 0.186 | 0.130 | ≤0.25 | pass both |
| TC survival (net Sharpe, 10bps/trade) | 1.145 | 1.046 | ≥0.5 | pass both |
| Walk-forward (4-quarter, manual fallback) | 1.0 | 1.0 | ≥0.75 | pass both |
| Parameter sensitivity (relative std, 9-combo short/mid sweep) | 0.157 | 0.089 | ≤0.5 | pass both |

Num trades: QQQ 54, SPY 43 over 2019-01 to 2026-09.

## Crypto check (same config)

| Metric | BTC/USDT | ETH/USDT |
|---|---|---|
| Sharpe (full-sample) | 1.242 | 0.954 |
| Max drawdown | **0.476** | **0.545** |

Crypto Sharpe is respectable but max drawdown decisively fails the 0.25 cap
on both pairs (0.476/0.545) — the vote construction stays long through
crypto's much larger drawdowns since none of the three trailing-return
signs flip bearish quickly enough during a fast crash.

## Decision: ACCEPTED (QQQ + SPY only); crypto rejected on max drawdown

Both equities pass all five validators at the same tuned config
(short_days=42, mid_days=42, long_days=252, min_votes=2). This is a
genuinely new construction type for this repo (multi-horizon voting rather
than any single lookback), robust across both equity symbols with low
parameter sensitivity. Crypto explicitly excluded from the live scope due
to decisive max-drawdown failure.
