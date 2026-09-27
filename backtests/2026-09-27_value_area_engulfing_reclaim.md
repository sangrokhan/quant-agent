# Value-Area Engulfing-Candle Reclaim Reversion — Backtest Report

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_value_area_engulfing_reclaim.py`
**Outcome:** REJECTED

## Hypothesis

Per LuxAlgo's "Value Area Reversion Signals" indicator
(https://www.luxalgo.com/library/indicator/value-area-reversion-signals,
published Aug 18 2026, read via `browser_exec` this iteration — `web_search`
was used for initial keyword discovery this cron trigger but LuxAlgo's
newest-sorted library listing was browsed directly with `browser_exec` to
find this specific unvisited indicator page): a rolling volume profile's
Value Area (VAL/VAH bounding `value_area_pct` of volume around the POC) —
when price breaks below VAL, fails to hold, then produces a bullish
ENGULFING candle re-entering the Value Area on expanding volume — signals a
failed breakdown that should travel back toward POC. Distinct from the
earlier-tested plain VAL-reclaim entry (`2026-09-10-001`) by requiring the
engulfing-candle pattern + volume-expansion confirmation filter rather than
any close-above-VAL bar.

## Grid test (Step 6)

`param_grid={lookback:[15,20,30], vol_mult:[1.2,1.5], max_hold_days:[6,10]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`
→ 144 cells total.

- **pass_fraction: 0.0278** (4/144 cells passed Sharpe>=1.0 & MDD<=0.25)
- by_asset_class: equity 4/72 passed, crypto 0/72 passed
- by_vol_regime: low 2/48, mid 2/48, high 0/48
- best_cell: `{lookback:15, vol_mult:1.2, max_hold_days:6}` SPY mid-vol, Sharpe 1.28
- worst_cell: same params but `max_hold_days:10`, QQQ mid-vol, Sharpe -1.23

Full grid: `grid_summary_value_area_engulfing_reclaim.json`

## Single-config validation (Step 7): best cell (SPY, lookback=15, vol_mult=1.2, max_hold_days=6), full sample 2019-01-01..2026-09-01

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ❌ | -0.221 | >= 1.0 |
| max_drawdown | ✅ | 0.044 | <= 0.25 |
| transaction_cost_survival | ❌ | -0.264 net Sharpe | >= 0.5 |
| walk_forward (manual 4-fold fallback; vectorbt RangeSplitter API unavailable in installed version) | ❌ | 0.5 pass_fraction (2/4 splits positive) | >= 0.75 |
| parameter_sensitivity | ✅ | 0.207 relative std | <= 0.5 |

Full evidence: `validators_value_area_engulfing_reclaim_spy.json`

## Decision

**REJECTED.** Only 2/5 validators passed. The grid's isolated mid-vol-regime
success on SPY at a narrow parameter combo did not generalize to the
full-sample single-config test — full-sample Sharpe was negative
(-0.221), confirming this is a narrow in-sample artifact of the mid-vol
tercile rather than a real edge. The pattern (engulfing-candle + volume
confirmation on VA reclaim) triggers too rarely (6 trades on SPY over 7+
years) to draw robust conclusions, and shows essentially zero signal on
crypto (0/72 grid cells passed). Strategy file and grid/validation JSON
kept as record of a rejected attempt.
