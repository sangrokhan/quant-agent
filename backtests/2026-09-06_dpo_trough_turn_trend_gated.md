# Backtest Report: DPO Trough-Turn Trend-Gated Cycle Strategy (REJECTED)

**Strategy file:** `strategies/2026-09-06_dpo_trough_turn_trend_gated.py`
**Date:** 2026-09-06
**Source:** https://gocharting.com/docs/charting/technical-indicator/oscillators/detrended-price-oscillator

## Hypothesis

Per GoCharting's DPO docs: "Buy when DPO reaches a historically significant
trough and turns up; sell when it reaches a peak and turns down," gated by
a trend filter (source explicitly warns DPO shouldn't be used standalone
for trend direction). Distinct from the two prior DPO strategies in this
repo (2026-09-04-056 zero-cross proxy; 2026-09-05-062 DPO+ADX+SAR triple
confirmation) -- this is the actual trough/peak-turn rule from the source.

## Step 6 — Grid test summary (216 cells: dpo_window[10,20,30] x
turn_window[3,5] x max_hold_days[10,15,20] x 2 asset classes x 2 symbols
each x 3 vol regimes)

- **Overall pass_fraction: 0.144** (31/216)
- **By asset class:** equity 31/108 (0.287), crypto 0/108 (decisive reject)
- **By vol regime:** low 28/72 (0.389), mid 3/72 (0.042), high 0/72 (0.0)
- **Best cell:** dpo_window=10, turn_window=5, max_hold_days=10, SPY, low-vol,
  Sharpe=2.87
- Only works narrowly in equity low-vol regime cells; degrades sharply in
  mid/high vol and fails completely on crypto.

## Step 7 — Single-config validation (best cell config, SPY, full sample
2019-01-01 to 2026-09-01)

Config: `dpo_window=10, turn_window=5, max_hold_days=10`

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **False** | 0.687 | >= 1.0 |
| Max drawdown | True | 0.218 | <= 0.25 |
| TC survival (10bps/trade, 158 trades) | **False** | net Sharpe 0.322 | >= 0.5 |

Full-sample Sharpe misses threshold and the strategy trades frequently
(158 trades over 7.7yr) so transaction costs erode most of the edge that
did exist in the best isolated low-vol grid cell. Skipped walk-forward and
parameter sensitivity given the decisive full-sample Sharpe + TC failure.

## Outcome: **REJECTED**

Fails Sharpe and transaction-cost survival on the best full-sample config
despite one narrow low-vol grid cell looking attractive in isolation --
classic case of grid cherry-picking not surviving full-sample confirmation
and consistent with the source's own warning that DPO shouldn't be used as
a standalone entry signal even with a trend filter added. Keeping the file
as a rejected-attempt record.
