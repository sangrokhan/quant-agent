# Backtest Report: UGA Pre-Holiday Effect, Trend-Gated (Rescue Attempt)

**Strategy file:** `strategies/2026-09-27_uga_pre_holiday_trendgate.py`
**Date:** 2026-09-27
**Source:** Self-constructed follow-up (no new external source this
iteration) -- direct rescue attempt on this same cron trigger's prior
near-miss 2026-09-27-016 (UGA pre-holiday D-5->D-1 hold, Sharpe 0.983,
all other validators passed).

## Hypothesis

Adding an SMA(trend_window) trend filter evaluated at the D-5 entry point
(only take the trade if close(D-5) > SMA(trend_window)) would avoid the
strategy's worst drawdown period (source article's own noted "most
significant drawdown in the months leading to the 2022 Russian invasion
of Ukraine") and push Sharpe above the 1.0 bar.

## Grid test summary (Step 6)

Grid: `entry_days_before in [3,5]` x `trend_window in [20,50,100]` x
equity {UGA, USO} + crypto {BTC/USDT, ETH/USDT} x 3 vol-regime terciles,
2010-2026.

- **Overall pass_fraction: 0.097 (7/72 cells)** -- notably WORSE than the
  ungated version's 0.229.
- **by_asset_class:** equity 3/36 (0.083); crypto 4/36 (0.111)
- best_cell is actually BTC/USDT (low-vol, Sharpe 1.47) -- not the
  intended UGA/USO target at all.

## Full-sample check (best UGA/USO configs from the grid)

| Symbol | entry_days_before | trend_window | Sharpe | MDD |
|---|---|---|---|---|
| UGA | 3 | 20 | 0.901 | 0.089 |
| UGA | 3 | 50 | 0.578 | 0.107 |
| UGA | 5 | 50 | 0.619 | 0.205 |
| USO | 3 | 20 | 0.560 | 0.089 |

## Decision: **REJECTED (rescue attempt failed)**

The trend filter does NOT rescue the near-miss -- every UGA/USO
trend-gated config tested has a LOWER Sharpe than the ungated
2026-09-27-016 baseline (UGA unfiltered `entry_days_before=5`: Sharpe
0.983; best trend-gated UGA config here `entry_days_before=3,
trend_window=20`: Sharpe 0.901). The filter does reduce drawdown
(MDD 0.089 vs 0.195 ungated) but at the cost of Sharpe, the opposite of
what was needed to clear the 1.0 bar. Confirms 2026-09-27-016's own
diagnostic guess was wrong: a simple SMA trend pre-filter is not the
right rescue mechanism for this strategy -- the source's own noted 2022
drawdown period was likely not avoidable by a trend filter evaluated only
at the D-5 entry point (a full holiday-window drawdown can still occur
even if the trend was positive 5 days earlier). Not pursued further this
iteration.
