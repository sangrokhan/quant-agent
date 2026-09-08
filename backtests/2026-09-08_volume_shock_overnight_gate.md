# Backtest Report: Volume-Shock Gated Overnight Return

**Strategy file:** `strategies/2026-09-08_volume_shock_overnight_gate.py`
**Date:** 2026-09-08
**Status:** REJECTED

## Hypothesis

Per Cartea, Cucuringu, Jin & Wilson, "Volume Shocks and Overnight Returns"
(2025, Oxford), summarized at
https://www.quantitativo.com/p/volume-shocks-and-overnight-returns:
unexpected intraday volume spikes predict abnormally high close-to-open
(overnight) returns, with no analogous intraday effect. Adapted to daily
OHLCV (no intraday volume feed available): gate an overnight-only hold
(entered at prior close, exited at next open, no intraday exposure) on a
rolling volume z-score exceeding `vol_shock_threshold`, instead of the
already-accepted trend/SMA gate (2026-09-08-053) or the rejected VIX-level
gate (2026-09-07-020).

## Full-sample single-config metrics (vol_window=40, vol_shock_threshold=0.5 — grid's best cell)

| Symbol | Sharpe | Max DD | Net Sharpe (after 5bps/trade) | Walk-forward pass fraction |
|---|---|---|---|---|
| SPY | -0.331 (fail, need ≥1.0) | 0.338 (fail, need ≤0.25) | -0.533 (fail, need ≥0.5) | 0.75 (pass) |
| QQQ | -0.097 (fail) | 0.311 (fail) | -0.347 (fail) | 0.75 (pass) |

## Step 6 grid summary (vol_window ∈ {10,20,40} × vol_shock_threshold ∈ {0.5,1.0,1.5}, equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, 3 vol-regime terciles)

- Total cells: 108, passed (Sharpe≥1.0 & MDD≤0.25): 5 → **pass_fraction 0.046**
- By asset class: equity 5/54 passed; crypto 0/54 passed (expected — no discrete overnight session for 24/7 crypto)
- By vol regime: low 0/36, **mid 5/36**, high 0/36 — edge concentrated entirely in the mid-volatility tercile
- Best cell: vol_window=40, vol_shock_threshold=0.5, SPY, mid-vol regime, Sharpe 1.322
- Worst cell: vol_window=10, vol_shock_threshold=1.0, QQQ, high-vol regime, Sharpe -1.176

The best grid cell's edge does not survive to the full-sample single-config
test (Sharpe flips negative), confirming the signal only works in a narrow
mid-vol-regime slice and is not a robust standalone gate. This mirrors this
repo's prior finding that ad-hoc volatility/attention-based gates on the
overnight-return premium (2026-09-07-020, VIX-level gate) underperform the
simple trend/SMA gate already accepted (2026-09-08-053).

## Verdict

REJECTED — full-sample Sharpe, max-drawdown, and transaction-cost-survival
all fail for both tested equities; grid pass_fraction 0.046 with the edge
concentrated in one narrow vol-regime tercile only. Walk-forward alone
passing (0.75) is not sufficient given the other three validators fail
decisively.
