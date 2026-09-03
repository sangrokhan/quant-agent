# Backtest Report: Balance of Power (BOP) Smoothed Threshold Crossover

**Strategy file:** `strategies/2026-09-04_bop_threshold_crossover.py`
**Knowledge base id:** 2026-09-04-071

## Hypothesis

Per IBKR Glossary + TradingView community synthesis: BOP = (Close-Open) /
(High-Low), a bounded -1..1 intrabar buyer/seller dominance measure,
smoothed with a rolling mean. Long entry when smoothed BOP crosses above
an entry threshold; exit when smoothed BOP crosses back below zero.
Distinct calculation basis from RVI (2026-09-04-061, 4-bar
triangular-weighted close-vs-open/high-low ratio) already tested.

Source: https://kr.tradingview.com/scripts/bop (Google search snippet) +
IBKR Glossary formula (web_search failed twice with a DDGS/Yahoo TLS
connection error, fell back to browser_exec; HowToTrade and LuxAlgo pages
both returned blocked/short content).

**Note on threshold recalibration:** the naively-cited TradingView
community threshold (0.8) never triggers on a 14-day-smoothed daily BOP
series (empirically ranges roughly -0.4 to +0.43 on QQQ 2019-2026) — it
was likely intended for unsmoothed intrabar BOP. Rescaled to a realistic
0.15-0.3 range based on the observed data distribution before grid
testing.

## Grid test summary

- Grid: `entry_threshold` in {0.15,0.2,0.3} x symbols
  {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol-regime terciles = 36 cells.
- pass_fraction: 0.222 (8/36)
- by_asset_class: equity 8/18, crypto 0/18
- by_vol_regime: low 6/12, mid 2/12, high 0/12
- best_cell: QQQ, entry_threshold=0.15, low-vol tercile, Sharpe 3.11
- worst_cell: SPY, entry_threshold=0.3, high-vol tercile, Sharpe -1.36

## Full-sample sweep (entry_threshold in {0.15,0.2,0.3})

| Symbol | th=0.15 | th=0.2 | th=0.3 |
|---|---|---|---|
| QQQ | **0.732** | 0.515 | -0.012 |
| SPY | 0.089 | 0.129 | 0.285 |

Primary config selected: `entry_threshold=0.2` (midpoint of tested range).

## Single-config validator suite (primary config, entry_threshold=0.2)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | 0.515 (fail, thr 1.0) | 0.129 (fail, thr 1.0) |
| Max drawdown | 0.250 (fail, thr 0.25, borderline) | 0.214 (pass) |
| TC survival | 0.478 (fail, thr 0.5, borderline) | 0.072 (fail) |
| Walk-forward | 4/4 splits positive (pass) | 2/4 splits positive (fail) |
| Parameter sensitivity | rel.std 0.758 (fail) | rel.std 0.503 (fail, borderline) |

## Outcome

**Rejected.** QQQ fails Sharpe, MDD (borderline), TC-survival (borderline),
and parameter sensitivity (highly unstable across the 3 tested thresholds
— Sharpe swings from 0.732 to -0.012). SPY fails 4 of 5 validators.
Crypto rejected decisively (0/18 grid cells).

## Notes

Novelty: first BOP (intrabar close-position-normalized-by-range) strategy
in this repo, distinct from RVI's 4-bar-weighted variant already tested.
The extreme parameter sensitivity (QQQ Sharpe swinging positive to
near-zero across a narrow 0.15-0.3 threshold band) suggests the strategy
is curve-fit to a specific threshold rather than capturing a robust edge —
a red flag consistent with several other rejected oscillator-threshold
strategies in this repo. A future loop could try BOP as a CONFIRMATION
filter on another signal rather than a standalone threshold-cross entry.
