# 2026-09-23 HMA Dual Crossover + RSI + Linear-Regression Regime Filter (SPY/QQQ/BTC/ETH)

## Hypothesis
Source: Google AI Overview (search: "Hull Moving Average crossover trading
strategy specific period rule backtest"), synthesizing a YouTube channel
"CodeTrading" HMA system, read via browser_exec Google SERP fallback
(web_search DDGS backend errored on this iteration's query).

Rule: Fast HMA(16) crossing above Slow HMA(65) is a long entry, confirmed by
RSI(14) > 52 and a positive 50-period linear-regression slope trend-regime
filter; exit on the reverse crossover. Source's native setup uses 4H
execution + daily regime timeframe; this repo adapted the rule logic to
whatever bar frequency `data/loaders.py` returns (1d equities, default
crypto interval), since exact multi-timeframe replication isn't supported
by the current loader interface.

Distinct from 2026-09-04-026 (single HMA vs price cross, rejected
near-miss): this uses a DUAL HMA crossover plus two additional confirmation
filters (RSI momentum, linear-regression regime), not a retune of the same
mechanism.

## Grid test summary (fast_period x [10,16,20], slow_period x [50,65],
rsi_threshold x [48,52]; symbols QQQ/SPY equity, BTC/USDT ETH/USDT crypto;
vol_regime_splits=3; 144 total cells)

- pass_fraction: 0.215 (31/144)
- by_asset_class: equity 13/72 (0.18), crypto 18/72 (0.25)
- by_vol_regime: low 26/48 (0.54), mid 5/48 (0.10), high 0/48 (0.00)
- best_cell: fast=16 slow=50 rsi_threshold=52, crypto ETH/USDT, mid-vol,
  Sharpe 2.21
- worst_cell: fast=10 slow=65 rsi_threshold=48, equity QQQ, high-vol,
  Sharpe -1.32
- Best full-grid config by average pass rate: fast=20 slow=50
  rsi_threshold=52 (5/12 cells passed, 0.417 pass fraction)

The pattern is decisively regime-dependent: works only in low realized-vol
terciles (0.54 pass rate) and essentially never in high-vol regimes (0/48).
This mirrors the general finding across many prior trend/momentum crossover
strategies in this KB: whipsaw dominates in high-vol regimes.

## Single-config validation (best full-grid config: fast=20, slow=50,
rsi_threshold=52), full multi-year period, NOT vol-regime-split

| Symbol | Sharpe | Passed (>=1.0) | Max DD | Passed (<=0.25) |
|--------|--------|-----------------|--------|-------------------|
| SPY    | 0.350  | No              | 0.090  | Yes                |
| QQQ    | 0.145  | No              | 0.184  | Yes                |
| BTC    | 0.351  | No              | 0.215  | Yes                |

A wider full-grid sweep (fast in {10,16,20}, slow in {50,65}, rsi_threshold
in {48,52}) found the single best full-period Sharpe across all
symbol/config combos was only 0.453 (fast=10, slow=50, rsi_threshold=48,
QQQ) -- still well short of the 1.0 threshold.

## Verdict: REJECTED

While the low-vol-regime terciles show attractive Sharpe (>1 on several
cells, up to 2.21 on ETH/USDT mid-vol), no full-period (unfiltered by
regime) config clears the Sharpe >= 1.0 bar on any tested symbol. The
regime-conditional edge is real but this repo's standard single-config
validator (full-period Sharpe) is the acceptance bar per Step 7/8, and it
fails across the board. Walk-forward/transaction-cost/parameter-sensitivity
validators were not run given the primary Sharpe gate already failed
(consistent with `suggested_workload=normal` guidance to run at minimum
Sharpe + MDD, and stop early on a clear full-period Sharpe miss).

Strategy file kept in `strategies/` as a record of a rejected attempt (not
a live strategy) — the regime-conditional near-miss (low-vol Sharpe up to
2.21) is worth revisiting in a future iteration with an EXPLICIT low-vol
regime gate baked into the entry rule (rather than testing unconditionally
and only observing after the fact that low-vol cells do well), similar to
the approach in `strategies/2026-09-03_bb_meanrev_qqq_volregime.py`.
