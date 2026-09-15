# Backtest Report: RSMK + RSI Dual Momentum-Recovery Gate

**Strategy file:** `strategies/2026-09-16_rsmk_rsi_dual_recovery_gate.py`
**Date:** 2026-09-16
**Hypothesis source:** Markos Katsanos, "A Low-Risk ETF Trading Strategy" (TASC October 2026 Traders' Tips, WealthLab implementation) — https://traders.com/documentation/feedbk_docs/2026/10/traderstips.html (visited this iteration via browser_exec; `web_search` DDGS backend failed with `RequestError`/TLS close-notify on every query attempted, so all research this iteration used the browser fallback).

## Hypothesis

Katsanos' article combines TWO independent momentum-recovery filters that
must agree before entry: (1) his own RSMK relative-strength-vs-benchmark
oscillator freshly turning up from a low level (not yet overextended), and
(2) short-period RSI showing an oversold-then-recovering pattern. This
repo's only prior standalone RSMK strategy (2026-09-12-153, MACD-style
signal-line crossover) was rejected. This iteration tests whether adding
the source's own RSI oversold-recovery AND-gate (which the prior attempt
omitted) rescues RSMK as a usable signal, adapted to a single-asset-vs-
benchmark long/flat system (benchmark fetched internally, same pattern as
`strategies/2026-09-08_pairs_zscore_cointegration.py`).

## Parameter search (Step 6, lightweight — 4 symbol/benchmark pairs x 3x3
`rscrit`/`rsi_oversold` grid = 36 cells, single vol-regime full-sample
Sharpe/MDD screen rather than the full 3-regime grid_test.py, given the
signal's low trade frequency makes per-vol-regime slicing degenerate for
several symbols)

| Symbol (bench) | Best config | Sharpe | MDD | Trade days |
|---|---|---|---|---|
| QQQ (SPY) | rscrit=2.0, rsi_os=30 | 1.032 | 0.072 | 212 |
| QQQ (SPY) | rscrit=1.0, rsi_os=30 | 1.158 | 0.149 | 308 |
| SPY (QQQ) | best of 9 configs | 0.088 | 0.161 | 192 | — decisively weak
| BTC/USDT (ETH/USDT) | best of 9 configs | 0.416 | 0.467 | 627 | — decisively weak
| ETH/USDT (BTC/USDT) | best of 9 configs | 0.533 | 0.408 | 406 | — decisively weak

Only QQQ (using SPY as the relative-strength benchmark) clears Sharpe>1.0
at reasonable MDD. SPY-vs-QQQ (the reverse pairing), and both crypto
pairings (BTC-vs-ETH, ETH-vs-BTC) all fail decisively at every grid point
tested — the signal appears QQQ/tech-momentum-specific rather than a
general relative-strength-recovery edge.

## Single-config validation (Step 7) — QQQ, rscrit=2.0, rsi_oversold=30.0

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.032 | ≥1.0 | PASS |
| Max drawdown | 0.072 | ≤0.25 | PASS |
| Net Sharpe after 10bps/trade costs | 0.975 | ≥0.5 | PASS (only 20 trades total, cost drag negligible) |
| Walk-forward (4 splits) | 1.0 (4/4 positive) | ≥0.75 | PASS |
| Parameter sensitivity (rel. std across 3x3 grid) | 0.416 | ≤0.5 | PASS (near the threshold — flagged as a near-miss-adjacent caveat; the signal is low-frequency (20 trades over ~8.5 years) so results should be treated as a smaller-sample finding than this repo's higher-turnover sizing-dial strategies) |

## Decision

**Accept: QQQ only** (benchmark SPY, all 5 validators pass). **Reject: SPY,
BTC/USDT, ETH/USDT** (decisive full-sample Sharpe failure at every tested
config for the reverse-benchmark and crypto pairings).

## Caveat for future loops

Only 20 trades over the full ~8.5-year sample — a smaller evidentiary base
than typical for this repo's daily-rebalanced sizing-dial family. The
parameter-sensitivity relative_std (0.416) is closer to the 0.5 rejection
threshold than most accepted strategies in this repo, so treat this as a
moderate-confidence accept rather than a robust one; a future loop
revisiting this idea should widen the parameter search before trusting it
further, or consider requiring a minimum trade count for acceptance.
