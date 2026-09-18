# Backtest Report: 3-Day RSI Oversold Bounce, Signal-Based Exit (SPY, rsi_oversold=20, max_hold_days=10)

**Date:** 2026-09-18
**Status:** ACCEPTED (SPY); QQQ near-miss, not accepted

## Hypothesis

Source: https://www.quantifiedstrategies.com/what-happens-when-stock-markets-are-oversold/

3-day RSI < 20 signals oversold -> enter at close. Source's own disclosed
exit rule: wait until the market "gets a solid up day in the opposite
direction and closes above yesterday's high" (signal-based exit on close
crossing above the PRIOR day's high), with a max_hold_days time-stop
backstop added per this repo's established safety-net pattern. Source's
SPY 1985-present backtest: 484 trades, avg gain 0.64%/trade, win rate
75%, CAGR 7.7%, MDD 26%, profit factor 2.5.

## Step 6 grid summary (`grid_result_rsi3_oversold_prevhigh_exit.json`)

- param_grid: `rsi_oversold` in [15, 20, 25], `max_hold_days` in [10, 20]
- symbols: equity (QQQ, SPY), crypto (BTC/USDT, ETH/USDT)
- vol_regime_splits: 3
- **pass_fraction: 0.25 (18/72 cells)**
- by_asset_class: equity 18/36, crypto 0/36 (decisive crypto reject)
- by_vol_regime: low 7/24, mid 6/24, high 5/24 -- notably passes across
  ALL THREE vol regimes (unlike every prior near-miss/rejection this
  cron trigger, which only passed in the isolated low-vol tercile)
- best_cell: SPY, rsi_oversold=20, max_hold_days=10, high-vol regime, Sharpe 1.45

## Step 7 single-config validation

### SPY (rsi_oversold=20, max_hold_days=10, full sample 2015-01-01 to 2026-09-01)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | pass | 1.190 | >= 1.0 |
| Max drawdown | pass | 0.123 | <= 0.25 |
| TC survival (10bps/trade, 141 trades) | pass | net Sharpe 0.954 | >= 0.5 |
| Walk-forward (4 splits) | pass | 1.0 pass fraction | >= 0.75 |
| Parameter sensitivity (6-combo grid) | pass | rel_std 0.158 | <= 0.5 |

**All 5 validators pass.** Very low parameter sensitivity (rel_std 0.158,
the lowest of any strategy tested this cron trigger) -- Sharpe is
consistently 1.09-1.45 across the entire (rsi_oversold, max_hold_days)
6-combo grid.

### QQQ (same config, quick check)

Sharpe 0.833 (< 1.0 threshold, near-miss fail), MDD 0.142 (pass), TC
survival net Sharpe 0.682 (pass). QQQ not accepted at this shared config
-- scope limited to SPY only for this iteration (no separate QQQ retune
attempted, given `suggested_workload=normal` and iteration budget already
well-used this trigger).

## Decision: ACCEPT (SPY only)

Unlike every other candidate tested this cron trigger (123 Pattern,
Key Reversal Day, Lower Highs/Lower Lows -- all showed a narrow low-vol-only
edge that failed full-sample), this strategy's edge holds up broadly
across all three volatility regimes on SPY, with very low parameter
sensitivity. Accepted for SPY; crypto decisively rejected (0/36); QQQ
near-miss, left untested for further tuning in a future iteration.

Strategy file kept live: `strategies/2026-09-18_rsi3_oversold_prevhigh_exit.py`.
