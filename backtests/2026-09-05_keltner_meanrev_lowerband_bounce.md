# Keltner Channel Mean-Reversion (Lower-Band Bounce) — Backtest Report

**Hypothesis:** Keltner Channel (EMA basis +/- ATR*mult bands) close crossing
below the lower band, gated by a longer-term SMA uptrend filter, signals an
oversold bounce entry (mean-reversion interpretation, distinct from this
repo's already-tested Keltner breakout, 2026-09-03-016); exit on close
reverting above the EMA basis, trend filter breaking, or a max_hold_days
time-stop.

**Source:** Multiple convergent community-forum snippets (Facebook trading
groups, synthesized via Google search): "BUY Signal: Price crosses below the
Lower Band and bounces back -> Mean-reversion buy"; exit "revert back from
the ... bottom of the band to the middle 20-period moving average".

**Strategy file:** `strategies/2026-09-05_keltner_meanrev_lowerband_bounce.py`

## Step 6 — Grid test summary (param_grid: atr_mult in [1.5,2.0,2.5] x
max_hold_days in [7,10,15]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 108, passed_cells: 10, **pass_fraction: 0.093** (weakest
  grid result of any strategy tested this run)
- by_asset_class: equity 10/54 (19%), crypto 0/54 (0%, decisive fail)
- by_vol_regime: low 5/36 (14%), mid 5/36 (14%), high 0/36 (0%)
- best_cell: atr_mult=1.5, max_hold_days=10, SPY, mid-vol, Sharpe=1.812
- worst_cell: atr_mult=2.5, max_hold_days=7, SPY, high-vol, Sharpe=-0.817

## Step 7 — Single-config validators (config: atr_mult=1.5,
max_hold_days=10, full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL -0.075 | **PASS** 1.088 |
| Max Drawdown (<= 0.25) | PASS 0.139 | PASS 0.077 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | FAIL -0.111 (18 trades) | PASS 0.981 (25 trades) |
| Parameter sensitivity (relative_std <= 0.5, atr_mult {1.5,2.0,2.5} sweep) | **FAIL 3.803** | **FAIL 2.117** |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **REJECTED**

QQQ fails Sharpe and transaction-cost survival outright (negative Sharpe).
SPY passes Sharpe, MDD, and tx-cost survival at atr_mult=1.5, but BOTH
symbols fail parameter sensitivity catastrophically (relative_std 3.8 and
2.1, far above the 0.5 threshold) -- the strategy's performance is wildly
unstable across the atr_mult sweep (very low trade counts of 18-25 mean
small changes in the band width produce large swings in which handful of
trades actually fire, a classic small-sample-size instability rather than a
genuine parameter-robust edge). Even though SPY's single best-config
numbers look superficially attractive, the parameter-sensitivity failure
means this is very likely a curve-fit result on a thin sample rather than a
durable edge. Rejected.
