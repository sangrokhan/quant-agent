# Relative Strength Comparative (RSC) vs Benchmark, MA-cross Momentum

**Hypothesis:** Per https://www.quantifiedstrategies.com/relative-strength-comparative/,
RSC = asset_close / benchmark_close identifies when an asset is
outperforming/underperforming a benchmark; used in momentum/asset-rotation
strategies. Source's specific rule is paywalled, so this implements the
standard textbook construction: long the asset when its RSC ratio crosses
above its own N-day SMA (fresh outperformance), exit when it crosses back
below, or a max-hold time-stop. First cross-asset relative-strength
strategy in this repo.

**Strategy file:** `strategies/2026-09-08_relative_strength_comparative.py`

## Test design note

Since this repo's grid-test harness (`run_strategy_grid`) evaluates one
symbol's OHLCV at a time and doesn't natively support a second
"benchmark" series, this strategy fetches its own benchmark internally via
`data/loaders.py` inside `generate_signals`, keyed by an explicit
`benchmark_symbol`/`asset_class` param. Tested manually (not via the
standard `run_strategy_grid` GridSpec, since that assumes a single price
series and doesn't vary a `benchmark_symbol` param) across natural pairs:

| Asset (long candidate) | Benchmark | rsc_window | Sharpe | MDD |
|---|---|---|---|---|
| QQQ | SPY | 10 | 1.141 PASS | 24.1% PASS (marginal) |
| QQQ | SPY | 20 | 0.609 FAIL | 26.9% FAIL |
| QQQ | SPY | 40 | 1.139 PASS | 32.2% FAIL |
| SPY | QQQ | 10/20/40 | all FAIL | all FAIL |
| ETH/USDT | BTC/USDT | 10/20/40 | all FAIL | all FAIL (58-64%) |
| BTC/USDT | ETH/USDT | 10/20/40 | all FAIL | all FAIL (81-92%) |

Only QQQ-vs-SPY (QQQ as the "stronger" tech-heavy asset relative to the
broader-market SPY benchmark) shows a viable signal; the reverse pairing
(SPY vs QQQ) and both crypto pairings fail decisively. Crypto pairings in
particular show extremely high trade counts (3,000-6,000+) and MDD
(58-92%) since BTC/ETH's relative-strength ratio whipsaws far more
than a 10-40-day SMA can smooth on daily bars for a young, volatile pair.

## Single-config validators (Step 7) -- QQQ vs SPY, rsc_window=10, max_hold_days=30

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.141 | >= 1.0 | PASS |
| Max drawdown | 24.1% | <= 25% | PASS (marginal) |
| TC-survival (10bps, 162 trades) | 0.929 | >= 0.5 | PASS |
| Walk-forward (manual 4-split) | 1.0 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (rsc_window 10/20/40 relative std) | 0.260 | <= 0.5 | PASS |

## Decision (Step 8)

**Accept, narrowly scoped to QQQ-vs-SPY relative strength, rsc_window=10,
max_hold_days=30.** All 5 validators pass, though MDD is a marginal pass
(24.1% vs the 25% ceiling) -- flag this as a genuine but fragile edge.
Does NOT generalize to the reverse pairing (SPY-vs-QQQ) or to either
crypto pairing (BTC/ETH), both of which fail decisively on every window
tested. This is a directional, asymmetric relationship (QQQ tends to
outperform SPY in bull-trending tech-led markets, not vice versa) rather
than a universal RSC-crossover edge.
