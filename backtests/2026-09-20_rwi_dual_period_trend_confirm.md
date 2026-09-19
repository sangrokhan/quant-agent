# Random Walk Index (RWI, Sibbet) Dual-Period Trend Confirmation — QQQ/SPY

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_rwi_dual_period_trend_confirm.py`
**Source:** Google AI-overview synthesis (RTMath/GoCharting/ForexBee) + https://www.strike.money/technical-analysis/random-walk-index

## Hypothesis

Long entry when long-term RWI High (30-period) > 1.0 (statistically
significant uptrend confirmed) AND short-term RWI Low (4-period) also > 1.0
(recent pullback statistically exhausted); exit when long-term RWI High
falls back below 1.0.

## Grid test (Step 6)

`param_grid={"long_period": [14, 20, 30], "short_period": [4, 6, 8]}`,
equity QQQ/SPY + crypto BTC/USDT/ETH/USDT, vol_regime_splits=3, 2019-2026.

- Overall pass fraction: 0.111 (12/108) — very low
- By asset class: equity 11/54 (0.204), crypto 1/54 (0.019)
- By vol regime: low 8/36, mid 3/36, high 1/36
- Best cell: long_period=30, short_period=4, QQQ, low-vol regime, Sharpe 1.91

## Single-config validation (Step 7) — long_period=30, short_period=4

| Symbol | Sharpe | MDD | Net-of-cost Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.214 (FAIL) | 0.098 (pass) | 0.172 (FAIL) | 0.75 (pass) | NaN (FAIL — grid_size 9, several cells produce 0/near-zero trades causing inf/nan in relative_std) |
| SPY | 0.452 (FAIL) | 0.068 (pass) | 0.349 (FAIL) | 0.75 (pass) | NaN (FAIL, same issue) |

The dual-1.0-threshold entry condition is extremely restrictive — only
11-16 trades over the full 2019-2026 sample for QQQ/SPY — leaving too few
trades to generate a robust edge or a meaningful parameter-sensitivity
sweep (several parameter combos in the 9-cell sweep produced 0 signals,
causing inf/nan in the relative-std computation, itself a decisive fail
signal about signal scarcity).

## Decision: **REJECTED** (Sharpe and tx-cost-survival both fail decisively on QQQ and SPY; parameter-sensitivity fails via NaN from signal scarcity)

Crypto grid pass_fraction is even worse (0.019/54).

Note for future loops: the dual RWI-High-AND-RWI-Low-both-above-1.0
condition is too rare to generate a tradeable strategy on daily bars for
this repo's symbol set. A future revisit could loosen the threshold (e.g.
0.5 per strike.money's "trend initiated" level) or drop the dual-condition
AND-gate in favor of a single RWI-High crossover, but this exact
construction should not be re-tried as-is.
