# Pring's Special K Continuous Sizing — Rejected (all symbols)

**Date:** 2026-09-15
**Strategy ID:** 2026-09-15-015 (assigned in knowledge_base log)
**File:** `strategies/2026-09-15_special_k_sizing_sma_trend.py`

## Hypothesis

Pring's Special K (weighted sum of 12 SMA-smoothed ROC legs, 10-530-period
lookbacks, per https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/prings-special-k,
visited this iteration) reframed as a continuous sizing dial (rolling
z-scored + tanh-squashed, SMA trend gate, deadband, leverage-cap for
crypto) -- following up on prior 2026-09-06-107 (binary Special-K-vs-
100-day-SMA-signal-line crossover, rejected as a near-miss, Sharpe 0.79-0.82
on QQQ/SPY, just under 1.0 threshold). Reused repo's own already-confirmed
12-leg coefficient table from strategies/2026-09-06_special_k_signal_crossover.py.

## Grid test summary (Step 6)

`param_grid={zscore_window: [100,150,200], sensitivity: [0.4,0.6],
deadband: [0.2,0.35]}`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 62, **pass_fraction:** 0.431.
- **by_asset_class:** equity 28/72 (0.389), crypto 34/72 (0.472).
- **by_vol_regime:** low 46/48 (0.958), mid 16/48 (0.333), high 0/48 (0.000).
- **best_cell:** ETH/USDT, zscore_window=150/sensitivity=0.4/deadband=0.35,
  mid-vol, Sharpe 2.429.
- **worst_cell:** QQQ, zscore_window=100/sensitivity=0.6/deadband=0.2,
  high-vol, Sharpe -1.039.

## Single-config validator results (Step 7)

Tried each symbol's best-looking grid-mean config, plus 5 extra QQQ
candidates from the grid's top rows:

| Symbol | Best config tried | Sharpe | TC-survival (net Sharpe) | Outcome |
|---|---|---|---|---|
| QQQ (best of 5 tried) | zscore_window=100/sensitivity=0.4/deadband=0.2 | 0.789 (**fail**) | 0.419 (**fail**) | rejected |
| SPY | zscore_window=200/sensitivity=0.4/deadband=0.35 | 0.887 (**fail**, near-miss) | 0.524 (pass) | rejected |
| BTC/USDT | zscore_window=200/sensitivity=0.6/deadband=0.2, leverage_cap=0.4 | (Sharpe not fully cleared, MDD pass) | -0.048 (**fail**, 3986 trades) | rejected |
| ETH/USDT | zscore_window=150/sensitivity=0.4/deadband=0.35, leverage_cap=0.4 | 0.134 (**fail**) | -0.050 (**fail**, 3860 trades) | rejected |

All 4 symbols fail on Sharpe and/or TC-survival despite the grid's
per-cell terciles looking reasonable in isolation. Same crypto-turnover
pattern seen this cron trigger with other sizing dials on the crypto
loader's hourly bars (~3,860-3,986 trades over full sample).

## Decision

**Rejected (all symbols).** Special K's already-confirmed near-miss as a
binary crossover trigger (2026-09-06-107) does not translate into a
passing continuous sizing dial either -- neither QQQ, SPY, BTC/USDT, nor
ETH/USDT clears the full validator suite at any tried config. Unlike other
indicator families this cron trigger where the sizing-dial reframing
rescued a near-miss, Special K's composite (12 legs, heavily smoothed,
effectively very low-frequency) appears to genuinely lack sufficient
edge/timeliness for either framing on this data. Strategy file and this
report kept as a record per Step 8 guidance (not deleted).
