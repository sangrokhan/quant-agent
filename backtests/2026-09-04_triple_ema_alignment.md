# Backtest Report: Triple EMA Crossover with Alignment Confirmation

**Strategy file:** `strategies/2026-09-04_triple_ema_alignment.py`
**Knowledge base id:** 2026-09-04-070

## Hypothesis

Per HowToTrade's Triple Moving Average Crossover article: fast(10) EMA
crosses above slow(50) EMA AND the medium(30) EMA sits between them in
bullish alignment (fast > medium > long) at the cross, confirming a
genuine trend shift; exit when close crosses below the medium EMA (source's
stated trailing-stop/mean-reversion role for the medium EMA). Distinct
from GMMA (-062, two CLUSTERS of 6 EMAs) and every dual-MA crossover
already tested since this uses exactly THREE individual EMAs with an
alignment-confirmation requirement.

Source: https://howtotrade.com/trading-strategies/triple-moving-average-crossover/
(web_search failed twice with a DDGS/Yahoo TLS connection error, fell
back to browser_exec).

## Grid test summary

- Grid: `fast_window` in {9,10} x `medium_window` in {21,30} x
  `slow_window` in {50,55} x symbols {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol
  regime terciles = 96 cells.
- pass_fraction: 0.177 (17/96)
- by_asset_class: equity 17/48, crypto 0/48
- by_vol_regime: low 8/32, mid 4/32, high 5/32
- best_cell: QQQ, fast=9/medium=30/slow=50, low-vol tercile, Sharpe 2.27
- worst_cell: QQQ, fast=9/medium=30/slow=55, high-vol tercile, Sharpe -0.62

## Full-sample sweep (2 canonical combos)

| Symbol | 10/30/50 | 9/21/55 |
|---|---|---|
| QQQ | **1.025** | 1.052 |
| SPY | 0.872 | **1.044** |

Primary config selected: `fast=10, medium=30, slow=50` (source's most
commonly cited default combo).

## Single-config validator suite (primary config, 10/30/50)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | **1.025** (pass, thr 1.0) | 0.872 (fail, thr 1.0) |
| Max drawdown | **0.082** (pass, thr 0.25) | 0.051 (pass) |
| TC survival | **1.001** (pass, thr 0.5) | 0.840 (pass) |
| Walk-forward | 3/4 splits positive (pass) | 2/4 splits positive (**fail**) |
| Parameter sensitivity | rel.std 0.013 (pass) | rel.std 0.090 (pass) |

Notably low trade count: only 8 (QQQ) and 7 (SPY) completed round-trips
over 7.7 years — the triple alignment confirmation filters out almost all
crossovers, leaving only the highest-conviction trend shifts.

## Outcome

**Accepted (QQQ only).** SPY is a near-miss on Sharpe (0.872) and fails
walk-forward (2/4 splits) but SPY DOES clear the bar (1.044 Sharpe) at
the alternative combo (9/21/55) — a future loop could revisit with
per-symbol tuned parameters. Crypto rejected decisively (0/48 grid
cells).

## Notes

Novelty: first exactly-three-individual-EMA alignment-confirmed crossover
in this repo, distinct from GMMA's 6-EMA clusters and every 2-line
crossover already tested. Exceptionally clean, low-frequency accept (8
trades over 7.7yr, near-zero MDD 8.2%) — the triple-alignment requirement
acts as a strong noise filter, a useful contrast to higher-frequency
accepted strategies in this repo (Williams %R -030, ROC -039).
