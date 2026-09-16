# Backtest Report: TD Sequential "Perfected" Buy Setup

**Strategy file:** `strategies/2026-09-17_td_sequential_perfected_setup.py`
**Hypothesis id:** 2026-09-17-017

## Hypothesis

Per https://sai-tai.com/other/econ/indicators-strategies/td-sequential/
(read via browser_exec after web_search backend failures this iteration —
DuckDuckGo/Yahoo TLS RequestError repeated 3x on multiple queries):
a raw TD Buy Setup (9 consecutive closes each below close[4] bars prior)
was already rejected in this repo (2026-09-04-032). This entry tests the
source's own "perfected setup" confirmation rule: the low of bar 8 or 9
must be <= the lows of bars 6 and 7, filtering for genuine intrabar
exhaustion structure rather than a naive close-only count. Distinct from
prior Countdown-confirmation variants (2026-09-08-079, 2026-09-09-031)
which extended the *count*, not the *structure* filter.

## Grid summary (scripts/run_grid_td_perfected.py)

param_grid: setup_count={8,9} x exit_sma_window={5,10} x max_hold_days={10,20}
x {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol-regime terciles = 96 cells

- pass_fraction: 0.1875 (18/96)
- by_asset_class: equity 12/48, crypto 6/48
- by_vol_regime: low 4/32, mid 2/32, high 12/32 (edge concentrated in
  high-vol tercile — same pattern flagged as an artifact in the original
  2026-09-04-032 rejection)
- best_cell: QQQ, setup_count=8/exit_sma_window=10/max_hold_days=20,
  high-vol tercile Sharpe 1.579

## Full-sample validation of best cell (scripts/validate_td_perfected.py)

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Walk-forward (4-split) |
|--------|--------|-----|------------------|------------------------|
| QQQ | 0.640 (fail, thr 1.0) | 0.096 (pass) | 0.570 (pass) | 1.00 (pass) |
| SPY | 0.150 (fail) | 0.287 (fail) | 0.099 (fail) | 0.75 (pass) |
| BTC/USDT | -0.021 (fail) | 0.569 (fail) | -0.076 (fail) | 0.50 (fail) |
| ETH/USDT | 0.082 (fail) | 0.425 (fail) | -0.025 (fail) | 0.75 (pass) |

Every symbol fails the primary Sharpe threshold at full sample despite the
grid's apparent best-cell edge — confirming (exactly like the base
2026-09-04-032 rejection) that the high-vol-tercile "edge" does not survive
outside that narrow slice. Crypto additionally shows anomalously high trade
counts (BTC 1356, ETH 1336 trades over 7.7yr) suggesting the perfected-setup
condition fires far more often on crypto's noisier bar-to-bar close/low
relationships than on equity, compounding transaction-cost drag.

## Decision: REJECTED

Sharpe fails decisively on all 4 symbols at full sample; MDD/TC also fail on
3/4 symbols. The "perfected" structural filter does not rescue the base
TD Buy Setup pattern in this repo's daily-bar universe.
