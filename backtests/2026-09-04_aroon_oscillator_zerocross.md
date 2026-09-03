# Backtest Report: Aroon Oscillator Zero-Line Crossover

**Strategy file:** `strategies/2026-09-04_aroon_oscillator_zerocross.py`
**Knowledge base id:** 2026-09-04-063

## Hypothesis

Per RunBacktest's Aroon Oscillator strategy page: Aroon Oscillator =
AroonUp - AroonDown. Long entry on the oscillator crossing above zero
(AroonUp > AroonDown, accelerating bullishness), exit when it crosses back
below zero. Distinct from this repo's prior Aroon-Down-only strategy
(2026-09-04-031, absolute-level thresholds on AroonDown alone) since this
uses the DIFFERENCE oscillator with a zero-line-cross rule, the more
standard Aroon Oscillator formulation.

Source: https://runbacktest.com/trading-strategies/aroon-oscillator

## Grid test summary

- Grid: `aroon_window` in {14,25,40} x symbols {QQQ,SPY,BTC/USDT,ETH/USDT}
  x 3 vol-regime terciles = 36 cells.
- pass_fraction: 0.278 (10/36)
- by_asset_class: equity 10/18, crypto 0/18
- by_vol_regime: low 6/12, mid 3/12, high 1/12
- best_cell: QQQ, aroon_window=25, low-vol tercile, Sharpe 2.66
- worst_cell: QQQ, aroon_window=40, high-vol tercile, Sharpe -0.38

## Full-sample sweep (aroon_window in {14,25,40})

| Symbol | w=14 | w=25 | w=40 |
|---|---|---|---|
| QQQ | 1.111 | **1.099** | 0.847 |
| SPY | **1.321** | 0.922 | 0.742 |

Primary config selected: `aroon_window=25` (source's default; also
non-decisive between the two, and QQQ clears the bar cleanly at 25).

## Single-config validator suite (primary config, aroon_window=25)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | **1.099** (pass, thr 1.0) | 0.922 (fail, thr 1.0) |
| Max drawdown | **0.214** (pass, thr 0.25) | 0.167 (pass) |
| TC survival | **1.064** (pass, thr 0.5) | 0.880 (pass) |
| Walk-forward (4 splits, 3/4 pos req.) | 3/4 positive (pass) | 3/4 positive (pass) |
| Parameter sensitivity | rel.std 0.119 (pass) | rel.std 0.243 (pass) |

## Outcome

**Accepted (QQQ only).** SPY is a near-miss (Sharpe 0.922 vs 1.0
threshold, all other validators pass) — note SPY's Sharpe is actually
stronger at the shorter aroon_window=14 (1.321), a future loop could
revisit with per-symbol tuned windows rather than one shared default.
Crypto rejected decisively (0/18 grid cells).

## Notes

Second Aroon-family strategy in this repo. Distinct novelty from -031
(AroonDown alone, absolute thresholds) confirmed — this is the standard
AroonUp-AroonDown difference oscillator with zero-line crossover logic.
