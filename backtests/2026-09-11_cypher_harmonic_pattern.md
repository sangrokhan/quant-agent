# Bullish Cypher Harmonic Pattern

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-11_cypher_harmonic_pattern.py`
**KB id:** 2026-09-11-100

## Hypothesis

Source: https://howtotrade.com/chart-patterns/cypher-harmonic-pattern/
(visited this iteration). The Cypher harmonic pattern (Darren Oglesbee) is
an XABCD 5-point pattern, distinct from every other harmonic pattern
already tested in this repo (AB=CD, Gartley, Bat, Crab, Butterfly) via its
C-extends-beyond-A structure (127.2-141.4% extension of XA, not a
retracement of AB) and its D-point defined as a 78.6% retracement of leg XC
(not XA or BC as in other patterns). Fifth and final classic harmonic
pattern for this repo, completing the harmonic-pattern set.

## Grid test

param_grid = `{pivot_window: [7,11,15], max_hold_days: [10,15,20]}`,
QQQ/SPY + BTC/ETH, vol_regime_splits=3, 2018-01-01 to 2026-09-01. 108 cells.

- **pass_fraction: 0.0** (0/108) — decisive rejection across every cell
- best cell: pivot_window=15, max_hold_days=20, SPY, high-vol, Sharpe 0.97
  (still below threshold)

## Single-config validators (best grid config)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | Infinity (0 trades — undefined) | 0.475 FAIL |
| Max Drawdown (<=0.25) | 0.0 (0 trades) | 0.049 PASS |
| TC survival | Infinity (0 trades) | 0.431 FAIL |
| Num trades | **0** | 8 |

## Outcome: REJECTED

Decisive rejection. The Cypher pattern's strict combined Fibonacci
requirements (B in [38.2%,61.8%] of XA AND C extending 127.2-141.4% beyond
A AND D at 78.6% retracement of XC, all simultaneously on a fractal-pivot
zigzag) are so restrictive that the pattern **never once formed on QQQ**
over the full 2018-2026 sample at any tested pivot_window, and formed only
8 times on SPY (statistically insufficient trade count, consistent with
every other harmonic-pattern rejection in this repo — same signal-scarcity
failure mode documented for WaveTrend extreme-zone crossover, Triple
Bottom, and other narrow multi-condition pattern strategies). This
completes the classic-harmonic-pattern family test set for this repo: 1
accepted (AB=CD), 4 rejected (Gartley, Bat, Crab, Cypher — Butterfly was
accepted per the index but should be reconfirmed), all sharing the same
core lesson that stacking 2-3 simultaneous strict Fibonacci-ratio
conditions on daily-bar equity/crypto data produces too few valid pattern
completions to backtest reliably.
