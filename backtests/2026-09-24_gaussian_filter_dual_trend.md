# Gaussian Filter Dual-Trend — Backtest Report

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_gaussian_filter_dual_trend.py`
**Source:** https://runbacktest.com/trading-strategies/gaussian-filter (read via browser_exec fallback; web_search DDGS backend errored on the initial "Standard Deviation Channel breakout" query)

## Hypothesis

A multi-pole Gaussian-weighted moving average (approximated here via repeated
EMA cascades, `poles` passes) gives an optimally-smoothed trend baseline.
Dual fast/slow Gaussian crossover defines the trend regime; a
`distance_threshold_pct` gate on price-vs-slow-Gaussian distance avoids
chasing extended breakouts. First Gaussian Filter entry in this repo (0
prior KB hits).

## Grid test summary (Step 6)

- Grid: `fast_period` in {8,10,14} x `slow_period` in {24,30,40} x
  `distance_threshold_pct` in {0.4,0.5,0.8}, symbols QQQ/SPY (equity),
  BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3. 324 total cells.
- **Overall pass_fraction: 0.102** (33/324)
- By asset class: equity 25/162 (0.154), crypto 8/162 (0.049)
- By vol regime: low 6/108 (0.056), mid 8/108 (0.074), high 19/108 (0.176)
  — strategy noticeably favors high-vol regimes (Gaussian-smoothed trend +
  distance gate performs better when trends are more decisive).
- Best cell: SPY, fast_period=14/slow_period=24/distance_threshold_pct=0.8,
  high-vol regime, Sharpe 1.89.
- Worst cell: ETH/USDT, fast_period=10/slow_period=40/distance_threshold_pct=0.8,
  low-vol regime, Sharpe -1.70.

## Single-config validation (Step 7)

### QQQ (fast_period=10, slow_period=30, distance_threshold_pct=0.4, period=20, poles=4, max_hold_days=15)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ❌ | 0.708 | 1.0 |
| max_drawdown | ✅ | 0.062 | 0.25 |
| transaction_cost_survival | ❌ | 0.431 (net Sharpe) | 0.5 |
| walk_forward | ✅ | 0.75 pass fraction | 0.75 |
| parameter_sensitivity | ❌ | 0.656 relative std | 0.5 |

**3/5 fail — QQQ rejected.**

### SPY (fast_period=14, slow_period=24, distance_threshold_pct=0.8, period=20, poles=4, max_hold_days=15)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ✅ | 1.259 | 1.0 |
| max_drawdown | ✅ | 0.041 | 0.25 |
| transaction_cost_survival | ✅ | 1.009 (net Sharpe) | 0.5 |
| walk_forward | ✅ | 1.0 pass fraction | 0.75 |
| parameter_sensitivity | ❌ | 6.95 relative std (mean Sharpe near-zero 0.053 across the grid, so relative-std blows up) | 0.5 |

**4/5 pass — only parameter_sensitivity fails.** SPY has an attractive
single-config result, but the strategy's performance is not robust across
nearby parameter values (many combos in the grid have near-zero or negative
average Sharpe), so this is a genuine (not spurious) sensitivity failure,
not a metric artifact.

## Decision (Step 8)

**Rejected** — neither QQQ nor SPY pass all 5 validators. QQQ fails 3/5.
SPY fails only parameter_sensitivity, but that's a real structural finding:
the strategy's edge is concentrated in a narrow parameter neighborhood
(fast_period=14/slow_period=24/distance_threshold_pct=0.8 specifically) and
does not generalize across the grid. Crypto (BTC/USDT, ETH/USDT) grid
pass_fraction is low (0.049) and was not pursued individually.

## Notes for future loops

- SPY near-miss: consider re-testing with a tighter/coarser parameter grid
  centered on (14, 24, 0.8) to see if a nearby region is more stable, or add
  a regime filter (e.g. restrict trading to high-vol regime only, since
  that's where 19/108 of all passing cells cluster) as a follow-up rescue
  attempt.
- The EMA-cascade approximation of a true N-pole Gaussian filter may not be
  as smooth/optimal as a proper Gaussian-kernel convolution — a future
  iteration could implement the exact convolution and see if it behaves
  differently (though this would be a data-processing nuance, not expected
  to change the qualitative regime-dependence finding).
