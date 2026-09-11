# Pre-NFP Close-to-Close Drift — Backtest Report (2026-09-12)

**Hypothesis:** Per https://www.quantifiedstrategies.com/the-friday-jobs-report-trading/
(visited this iteration), the source's own disclosed backtest found the best
jobs-report calendar variant is entering at the close the day BEFORE the
first-Friday-of-month jobs report and exiting at the close of the report day
itself (avg claimed gain ~0.3%/trade), rather than the plain open-to-close
intraday trade on the report day (already tested/rejected in this repo,
id 2026-09-11-085, net Sharpe negative after costs). This strategy tests
that close(t-1)->close(first-Friday) variant, with `hold_days_before` /
`hold_days_after` as grid-tunable extensions.

Strategy file: `strategies/2026-09-12_pre_nfp_close_to_close_drift.py`
(REJECTED — kept as a record of a rejected attempt).

## Step 6 — Grid summary

`param_grid={hold_days_before: [1,2], hold_days_after: [0,1]}`,
`symbols={equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, period 2016-01-01 to 2026-09-01.

- total_cells=48, passed_cells=14, **pass_fraction=0.292**
- by_asset_class: equity 14/24, crypto 0/24 (decisive crypto rejection)
- by_vol_regime: low 6/16, mid 8/16, high 0/16 (decisive high-vol rejection)
- best_cell: QQQ, hold_days_before=1/hold_days_after=0, mid-vol regime, Sharpe 2.228
- worst_cell: QQQ, hold_days_before=1/hold_days_after=1, high-vol regime, Sharpe -1.606

The grid's encouraging mid-vol-regime Sharpe (2.23) does not survive to the
full-sample check below — a classic narrow-slice-only pattern.

## Step 7 — Full-sample validators (best grid config: hold_days_before=1, hold_days_after=0)

| Metric | QQQ | SPY | Threshold | Passed (QQQ / SPY) |
|---|---|---|---|---|
| Sharpe ratio | -0.128 | 0.034 | >=1.0 | No / No |
| Max drawdown | 0.238 | 0.178 | <=0.25 | Yes / Yes |
| Net Sharpe after 10bps costs (128 trades) | -0.287 | -0.183 | >=0.5 | No / No |
| Walk-forward (4-split, manual, RangeSplitter unavailable) | 0.5 (2/4) | 0.75 (3/4) | >=0.75 | No / Yes |
| Parameter sensitivity (relative std across 4-combo grid) | 16.60 | 1.21 | <=0.5 | No / No |

## Step 8 — Decision: **REJECTED**

Full-sample Sharpe is negative-to-near-zero on both symbols, net-of-cost
Sharpe is decisively negative, and parameter sensitivity is extremely high
(QQQ relative_std 16.6 — the 4-combo grid's mean Sharpe is nearly zero with
large variance, meaning small calendar-window tweaks flip the sign of the
edge entirely). This confirms the same conclusion as the already-tested
open-to-close-only NFP variant (2026-09-11-085): the source's own disclosed
raw average per-trade gain is real in isolation but is both too small to
survive realistic transaction costs and not robust to the exact
hold-window definition. Crypto rejected decisively (0/24 grid cells).
