# Time Segmented Volume (TSV, Worden Brothers) Zero-Line + Signal Crossover — QQQ/SPY

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_tsv_zeroline_signal_crossover.py`
**Source:** Google AI-overview synthesis + https://www.quantifiedstrategies.com/time-segmented-volume/

## Hypothesis

TSV sums price-change-signed volume over a rolling segment window (unlike
cumulative OBV/PVT, TSV re-sums over a fixed window, making it more
responsive). Long entry: TSV crosses above zero AND above its own
signal-line MA; exit: TSV falls below zero or below the signal line.

## Grid test (Step 6)

`param_grid={"segment_period": [9, 13, 21], "signal_period": [9, 13, 21]}`,
equity QQQ/SPY + crypto BTC/USDT/ETH/USDT, vol_regime_splits=3, 2019-2026.

- Overall pass fraction: 0.389 (42/108)
- By asset class: equity 28/54 (0.519), crypto 14/54 (0.259)
- By vol regime: low 26/36 (0.722), mid 10/36 (0.278), high 6/36 (0.167)
- Best cell: segment_period=21, signal_period=21, QQQ, low-vol regime, Sharpe 2.27

## Single-config validation (Step 7) — segment_period=21, signal_period=21

| Symbol | Sharpe | MDD | Net-of-cost Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.298 (pass) | 0.182 (pass) | 1.160 (pass) | 1.0 (pass) | **0.511 (FAIL, marginally above 0.5 threshold)** |
| SPY | **0.902 (FAIL, marginally below 1.0)** | 0.110 (pass) | 0.756 (pass) | 1.0 (pass) | 0.416 (pass) |
| BTC/USDT | 0.221 (FAIL) | 0.289 (FAIL) | 0.001 (FAIL) | 1.0 (pass) | 0.338 (pass) |
| ETH/USDT | 0.311 (FAIL) | 0.355 (FAIL) | 0.056 (FAIL) | 1.0 (pass) | 0.255 (pass) |

QQQ has a strong headline Sharpe (1.298) but the 9-cell period sweep ranges
from 0.27 to 1.42 (a very wide spread relative to the mean), causing
parameter_sensitivity to marginally fail (0.511 vs 0.5 threshold) -- the
edge is real but fragile to the exact segment/signal period choice. SPY
independently misses the Sharpe threshold (0.902) at this same config.

## Decision: **REJECTED** (QQQ fails parameter_sensitivity marginally, SPY fails Sharpe marginally -- neither symbol clears all 5 validators; crypto rejected decisively on Sharpe/MDD/tx-cost with 2400+ trades)

This is a near-miss worth revisiting: QQQ's Sharpe/MDD/walk-forward/
tx-cost-survival all pass comfortably, only parameter_sensitivity is the
blocker, and it fails only marginally (0.511 vs 0.5). A future iteration
could retry with a tighter, less-dispersed parameter grid (e.g.
segment_period in [17,21,25] instead of [9,13,21]) to see if the
sensitivity measure stabilizes, or add a regime/trend filter to make the
edge more robust across periods.
