# Backtest Report: Bulkowski Rectangle Top Upward Breakout (QQQ accepted, SPY rejected)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_rectangle_top_breakout.py`
**Source:** https://thepatternsite.com/recttops.html (Thomas Bulkowski's
"Encyclopedia of Chart Patterns" stats page; read via browser_exec — web_search's
DDGS backend returned unrelated/garbage results this iteration).

## Hypothesis
Rectangle Top: a prior uptrend consolidates into a tight, near-horizontal
range (parallel support/resistance, touched repeatedly). An upward
breakout above resistance (close confirmation) continues the prior
uptrend. Per Bulkowski's own published statistics, Rectangle Top upward
breakouts rank 4th out of 39 bullish chart patterns studied — a notably
stronger prior than most chart-pattern strategies already tested in this
repo. Exit uses Bulkowski's own "Measure Rule" (height=resistance-support,
target=resistance + height * 78%, the source's own disclosed "percentage
meeting price target" for upward breakouts). First Rectangle pattern entry
in this repo (0 prior index hits) — distinct from prior Triangle-family
entries (converging trendlines) because Rectangles require PARALLEL,
non-converging boundaries.

## Grid summary (Step 6)
`param_grid={"range_window": [15, 20, 30], "max_range_pct": [0.05, 0.08, 0.12]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3` (normal workload).

- total_cells: 108, passed_cells: 18, **pass_fraction: 0.167**
- by_asset_class: equity 11/54, crypto 7/54
- by_vol_regime: low 17/36, mid 1/36, high 0/36 (edge concentrated almost
  entirely in low-vol regime)
- best_cell: range_window=15, max_range_pct=0.12, QQQ, low-vol, Sharpe 2.770

## Single-config validators (best cell: range_window=15, max_range_pct=0.12)

### QQQ
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample, 148 trades) | **PASS** | 1.344 | >= 1.0 |
| Max drawdown | **PASS** | 0.121 | <= 0.25 |
| Transaction cost survival (10bps/trade) | **PASS** | net Sharpe 0.974 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | known repo `vectorbt.utils.splitting` bug |
| Parameter sensitivity (20-combo sweep) | **PASS** | rel_std 0.310 | <= 0.5 |

### SPY (same config)
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample, 180 trades) | **FAIL** | 0.386 | >= 1.0 |
| Max drawdown | PASS | 0.153 | <= 0.25 |
| Transaction cost survival | **FAIL** | net Sharpe -0.0002 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | same repo bug |
| Parameter sensitivity | not tested | n/a | n/a (decisive Sharpe/TC fail already) |

## Decision: ACCEPT (QQQ only), REJECT (SPY)
QQQ clears every runnable validator with comfortable margin at the grid's
best cell. SPY fails decisively at the identical config — 180 trades vs
QQQ's 148 (this range_window/max_range_pct config trades noticeably more
often on SPY, chopping through more failed-consolidation whipsaws) and
Sharpe collapses to near-zero after costs. Crypto not separately validated
(grid showed only 7/54 crypto cells passing, comparably weak to SPY) —
flagged as a future rescue candidate (per-symbol retune following this
repo's established pattern) but not pursued this iteration.
