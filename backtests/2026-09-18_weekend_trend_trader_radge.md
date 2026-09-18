# 2026-09-18-072: Nick Radge Weekend Trend Trader (Weekly Breakout + Regime + Trailing Stop)

## Hypothesis

Per the ThinkorSwim code posted at usethinkscript.com
(https://usethinkscript.com/threads/weekend-trend-trader-by-nick-radge-strategy-for-thinkorswim.669/),
Nick Radge's "Weekend Trend Trader" (fully disclosed numeric rule,
resolving the "paywalled" concern noted in this repo's earlier
2026-09-11-088): weekly-timeframe entry on a 20-week high + market-index
above its 10-week SMA + 20-week ROC > 30%; asymmetric trailing stop (40%
below recent high in an uptrend regime, tightening to 10% if regime flips
down), stop only ratchets up.

Adapted single-symbol (no genuine index-membership data available): uses
the traded asset's own 10-week SMA as a self-referential regime proxy
instead of an external index, isolating the entry/exit MECHANICS from the
infeasible cross-sectional universe-scanning aspect.

Source: https://usethinkscript.com/threads/weekend-trend-trader-by-nick-radge-strategy-for-thinkorswim.669/

## Parameter scan (roc_threshold in [0.15,0.30,0.45] x high_window in
[13,20,26] x init_trail_pct in [0.25,0.40], equity=[QQQ,SPY]
crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2018-01-01..2026-09-01)

- total_cells=216, passed_cells=48, pass_fraction=0.222
- by_asset_class: equity 44/108, crypto 4/108
- by_vol_regime: low 32/72, mid 0/72, high 16/72
- Best average-across-regimes config: **SPY, roc_threshold=0.15,
  high_window=20, init_trail_pct=0.4**, avg Sharpe 0.842, pass 2/3 vol
  regimes.

## Single-config validation (SPY, roc_threshold=0.15, high_window=20,
init_trail_pct=0.4, 2018-01-01..2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.696 | 1.0 | **fail** |
| Max drawdown | 0.190 | 0.25 | pass |
| Net Sharpe after costs (10bps/trade, 7 trades) | 0.687 | 0.5 | pass |
| Walk-forward (4 splits, manual substitute*) | 1.00 (4/4) | 0.75 | pass |
| Parameter sensitivity (relative std, 16-combo SPY grid) | 0.156 | 0.5 | pass |

\* `validation/validators.py::check_walk_forward` errors on the installed
vectorbt 1.1.0; substituted a manual 4-equal-split walk-forward (established
fallback).

## Decision

**Rejected.** Full-sample Sharpe (0.696) misses the 1.0 threshold by a
wide-ish margin despite every other validator passing cleanly, including a
very low parameter-sensitivity relative std (0.156, the most stable grid
result seen this cron trigger). Only 7 trades over 8.7 years -- the
20-week-high + 30%-ROC-equivalent entry filter (best config used
15%-threshold, less restrictive than the source's stated 30%) is quite
rare, which limits statistical power even though the edge that does fire
looks directionally real (positive Sharpe in all 4 walk-forward splits).
The self-referential single-symbol regime-filter substitution (asset's own
10-week SMA instead of a genuine external index) is the most likely source
of degraded edge versus the source's own claimed system -- a future
iteration could try substituting the S&P 500 (SPY itself, or a proxy
index) as the fixed external regime reference for OTHER assets (e.g. gate
QQQ's entries on SPY's own regime, keeping QQQ's own new-high/ROC
triggers), which would more faithfully replicate the source's
broad-market-filter design than the self-referential approach used here.
