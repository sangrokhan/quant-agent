# Backtest Report: McGinley Dynamic Crossunder, Fixed-Hold Mean Reversion

**Strategy file:** `strategies/2026-09-08_mcginley_crossunder_fixedhold.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Per QuantifiedStrategies.com's own disclosed McGinley Dynamic backtest
(https://www.quantifiedstrategies.com/mcginley-dynamic/), their "Strategy 3":
buy SPY at close when close crosses below the N-day McGinley Dynamic, sell
after a FIXED N-day hold (no signal-based exit). Source's own results table
shows short MD periods (5-25) work best, average gain-per-trade rising with
longer fixed holds. Distinct from this repo's existing McGinley Dynamic
strategy (2026-09-04-127, dual-line fast/slow crossover trend-following,
signal-based exit) via single-line price-crossunder trigger + fixed-day exit.

## Grid test summary (Step 6)

`md_period` in [5,10,25] x `hold_days` in [5,10,20], symbols
equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2018-01-01..2026-09-01.

- total_cells: 108, passed_cells: 16, **pass_fraction: 0.148**
- by_asset_class: equity 16/54, crypto **0/54** (decisive)
- by_vol_regime: **low 13/36**, mid 2/36, high 1/36 -- overwhelmingly
  concentrated in the low-volatility tercile
- best_cell: `{md_period:10, hold_days:10}` SPY low-vol, Sharpe 2.870,
  MDD 0.042 -- a very strong slice result

## Single-config validators (Step 7): SPY, md_period=10, hold_days=10, full
sample 2018-01-01..2026-09-01

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full sample) | ❌ | 0.707 | ≥ 1.0 |
| max_drawdown | ❌ | 0.349 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 103 trades) | ✅ | net Sharpe 0.603 | ≥ 0.5 |
| parameter_sensitivity (7 nearby cells: md_period x hold_days combos on SPY low-vol) | ✅ | relative_std 0.238 | ≤ 0.5 |

Walk-forward skipped: full-sample Sharpe/MDD already decisively fail, no
value in further validators under `suggested_workload=normal` budget.

## Decision: REJECT

The low-vol-regime grid slice looks excellent (Sharpe up to 2.87), but this
is exactly the pattern this repo has repeatedly seen with regime-narrow
strategies (e.g. 2026-09-04-052 VWAP bands): a mean-reversion rule that only
works when volatility is already low doesn't survive being tested across the
full sample, which includes the mid/high-vol regimes (2020 COVID crash, 2022
rate-hike drawdown) where the fixed-hold exit (no stop-loss at all) lets
losing positions run for the full hold_days regardless of adverse moves --
explaining the full-sample max drawdown blowing out to 0.349 vs the 0.25
budget. Crypto categorically 0/54. Honest scope: this is a low-vol-regime-only
tactic, and the source's own backtest (Strategy 3, no regime conditioning
at all) apparently benefited from a sample period/instrument mix that didn't
expose this weakness as starkly.
