# Backtest Report: ZLEMA Dual Crossover

**Strategy file:** `strategies/2026-09-04_zlema_dual_crossover.py`
**Knowledge base id:** 2026-09-04-066

## Hypothesis

Per Google AI-overview + ArrowAlgo/StockGro synthesis: Zero-Lag EMA
(ZLEMA) de-lags price via `de_lagged = 2*price - price.shift(lag)`,
`lag=(period-1)/2`, then applies a standard EMA. Distinct construction
from every prior MA in this repo (HMA nests WMAs, KAMA adapts smoothing
via Efficiency Ratio). Dual-ZLEMA crossover: fast ZLEMA crosses above slow
ZLEMA = long entry, opposite cross = exit.

Source: Google AI-overview synthesis (web_search failed with a
DDGS/Yahoo TLS connection error, fell back to browser_exec).

## Grid test summary

- Grid: `fast_window` in {10,20} x `slow_window` in {30,100} x symbols
  {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol-regime terciles = 48 cells.
- pass_fraction: 0.25 (12/48)
- by_asset_class: equity 12/24, crypto 0/24
- by_vol_regime: low 7/16, mid 4/16, high 1/16
- best_cell: QQQ, fast=20/slow=100, low-vol tercile, Sharpe 2.92
- worst_cell: QQQ, fast=10/slow=100, high-vol tercile, Sharpe -0.43

## Full-sample sweep (4 fast/slow combos)

| Symbol | 10/30 | 20/30 | 10/100 | 20/100 |
|---|---|---|---|---|
| QQQ | 1.012 | 0.868 | 0.882 | **1.360** |
| SPY | 0.748 | 0.848 | 0.774 | 0.697 |

Primary config selected: `fast_window=20, slow_window=100` (best full-sample
on QQQ, consistent with the repo's general pattern favoring longer/slower
crossover pairs).

## Single-config validator suite (primary config, fast=20/slow=100)

| Validator | QQQ | SPY (best combo, 10/30) |
|---|---|---|
| Sharpe ratio | **1.360** (pass) | 0.748/0.848 (fail at all 4 combos) |
| Max drawdown | **0.205** (pass) | 0.219 (pass) |
| TC survival | **1.321** (pass) | 0.639 (pass) |
| Walk-forward | 3/4 splits positive (pass) | 3/4 splits positive (pass) |
| Parameter sensitivity | rel.std 0.192 (pass) | rel.std 0.071 (pass) |

## Outcome

**Accepted (QQQ only).** SPY fails Sharpe decisively at every one of the 4
tested fast/slow combos (best 0.848 at fast=20/slow=30) — not a near-miss.
Crypto rejected decisively (0/24 grid cells).

## Notes

Novelty: first ZLEMA (de-lag-via-price-extrapolation construction) MA
crossover strategy in this repo, distinct from HMA/KAMA/VWMA/SMA/EMA
crossovers already tested. QQQ accept at fast=20/slow=100 continues the
repo's finding that longer/slower crossover pairs outperform on this
sample (cf. VWMA -060 fast=10/slow=100).
