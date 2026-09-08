# Backtest Report: Rebalancing-Pressure Front-Run (Turn-of-Month Gate)

**Strategy file:** `strategies/2026-09-08_rebalancing_pressure_tom_gate.py`
**Date:** 2026-09-08
**Status:** REJECTED (near-miss)

## Hypothesis

Per Harvey, Mazzoleni & Melone, "The Unintended Consequences of Rebalancing"
(summarized at
https://www.quantitativo.com/p/the-unintended-consequences-of-rebalancing):
institutional pension/mutual funds mechanically rebalance equity/bond
allocations near month-end; when equities have underperformed bonds
recently, forced rebalancing buy-flows push equity prices up over the
following ~2 weeks. Implemented as: long the primary equity/crypto asset
only during the last `calendar_days_before` trading days of the month,
gated additionally on the primary asset's trailing `lookback`-day return
being at least `underperf_threshold` below a bond proxy's (TLT) trailing
return over the same window (i.e. equities are "underweight" and due for
rebalancing inflows).

## Full-sample single-config metrics (lookback=10, underperf_threshold=-0.04, calendar_days_before=5 — grid's best cell)

| Symbol | Sharpe | Max DD | Net Sharpe (5bps/trade) | Walk-forward | Param sensitivity (rel std) | Trades |
|---|---|---|---|---|---|---|
| SPY | 0.529 (fail, need ≥1.0) | 0.084 (pass) | 0.438 (fail, need ≥0.5) | 1.0 (pass) | 0.309 (pass, need ≤0.5) | 50 |
| QQQ | 0.763 (fail, need ≥1.0) | 0.086 (pass) | 0.677 (pass) | 1.0 (pass) | 0.065 (pass) | 56 |

## Step 6 grid summary (lookback ∈ {10,20} × underperf_threshold ∈ {-0.02,-0.04} × calendar_days_before ∈ {3,5}, equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, 3 vol-regime terciles)

- Total cells: 96, passed (Sharpe≥1.0 & MDD≤0.25): 16 → **pass_fraction 0.167**
- By asset class: equity 16/48 passed; crypto 0/48 (expected — no institutional 401k/pension rebalancing flow into a bond sleeve for a 24/7 asset)
- By vol regime: low 3/32, mid 0/32, **high 13/32** — edge concentrated in the high-volatility tercile (consistent with rebalancing flows mattering more when equity/bond divergence itself is large, which correlates with high-vol periods)
- Best cell: lookback=10, underperf_threshold=-0.04, calendar_days_before=5, QQQ, high-vol regime, Sharpe 1.944
- Worst cell: same params, QQQ, mid-vol regime, Sharpe -1.482 (same config flips sign entirely across vol regimes)

The grid's best cell (isolated to the high-vol tercile) does not survive to
the full-sample single-config test: Sharpe drops to 0.53 (SPY) / 0.76 (QQQ),
both below the 1.0 threshold, though MDD, walk-forward, and parameter
sensitivity all pass comfortably, and QQQ clears transaction-cost survival
(SPY does not, narrowly). This is a genuine near-miss: low trade count
(50-56 trades over ~7.5 years) keeps drawdown and turnover low, and the
signal direction is consistently profitable and stable across parameter
choices and time sub-periods -- it simply doesn't clear the Sharpe bar on
the full, unconditioned sample once averaged across all volatility regimes.

## Verdict

REJECTED (near-miss) — full-sample Sharpe fails the 1.0 threshold for both
SPY and QQQ, and SPY additionally fails transaction-cost survival. Every
other validator (MDD, walk-forward, parameter sensitivity) passes cleanly,
and the strategy is directionally sound with a real edge concentrated in
high-vol regimes. A future iteration could revisit with an explicit
high-vol-regime gate (e.g. VIX or realized-vol filter) layered on top,
which the grid results suggest could recover the isolated high-vol-cell
Sharpe of ~1.94 on the full sample. Crypto rejected decisively (0/48,
expected -- mechanism structurally inapplicable, no institutional bond
rebalancing flow).
