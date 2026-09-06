# Twiggs Money Flow (TMF) Signal-Line Crossover, Trend-Gated

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_twiggs_money_flow_signal_crossover.py`
**Knowledge base id:** 2026-09-06-143

## Hypothesis

Per quantifiedstrategies.com's Twiggs Money Flow article
(https://www.quantifiedstrategies.com/twiggs-money-flow/): "Some traders and
analysts may add an EMA of the indicator as a signal line and use the signal
line crossovers as their buy and sell signals." Tests the **signal-line
crossover** variant (distinct from the already-tested zero-line-crossover
variant, id 2026-09-05-002), gated by a close > SMA(trend_window) uptrend
filter. Long entry when TMF crosses above its EMA signal line while in an
uptrend; exit on the reverse cross, trend break, or a max_hold_days time-stop.

TMF formula (Colin Twiggs): true-range-weighted (gap-aware) refinement of
Chaikin Money Flow, using EMA smoothing instead of CMF's rolling sum.

## Grid test (Step 6)

324 cells: `tmf_window` in [14,21,34] x `signal_window` in [5,9,13] x
`max_hold_days` in [10,15,20] x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol
terciles.

- **Overall pass_fraction:** 0.108 (35/324)
- **by_asset_class:** equity 35/162 (0.216); crypto 0/162 (decisive reject)
- **by_vol_regime:** low 29/108 (0.269); mid 0/108 (0.0); high 6/108 (0.056)
- **Best cell:** tmf_window=34/signal_window=13/max_hold_days=20, QQQ,
  low-vol regime, Sharpe=1.72

## Single-config validators (best-cell config, QQQ full sample)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.495 | 1.0 | **FAIL** |
| Max drawdown | 0.158 | 0.25 | pass |
| Transaction cost survival (10bps/trade, 180 trades) | 0.201 | 0.5 | **FAIL** |

Walk-forward/parameter-sensitivity skipped given decisive full-sample
Sharpe+TC failure (per RESEARCH_LOOP.md Step 7 guidance).

## Decision: REJECTED

The grid's best cell (isolated low-vol QQQ slice, Sharpe 1.72) does not
survive full-sample confirmation (Sharpe collapses to 0.495) — a classic
narrow-slice cherry-pick, the same pattern seen repeatedly in this repo
(e.g. STARC Bands 2026-09-06-141, Disparity Index 2026-09-06-140). Mid-vol
regime is a decisive 0/108 across the whole grid, and crypto is decisively
rejected (0/162). Only works, if at all, in a narrow low-vol equity slice
that isn't statistically robust once tested on the full sample.
