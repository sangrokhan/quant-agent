# Turn-of-the-Month (TOM) Equity Seasonality — Backtest Report

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-11_turn_of_month_seasonality.py`
**Source:** Google AI-overview synthesis of ScienceDirect/QuantPedia/Forbes coverage
of the Turn-of-the-Month equity anomaly.

## Hypothesis

Long equities during the last several trading days of a month through the
first few trading days of the next month (institutional month-end cash
flows: payroll, pension rebalancing), flat the rest of the month. Pure
calendar rule, no indicators.

## Grid test summary (Step 6)

`scripts/run_grid_tom.py` — param grid `entry_days_before_month_end∈{2,4,6}`,
`exit_days_into_month∈{1,2,3}` × symbols `{QQQ,SPY,BTC/USDT,ETH/USDT}` × 3
vol-regime terciles (108 total cells).

- **pass_fraction: 0.241** (26/108)
- **by_asset_class:** equity 26/54 passed, **crypto 0/54 passed**
- **by_vol_regime:** low 17/36, mid 4/36, high 5/36
- **best_cell:** QQQ, entry_days_before_month_end=6/exit_days_into_month=2, low-vol, Sharpe 1.81

## Single-config validators (Step 7) — best grid config (entry=6, exit=2), full sample 2010-2026

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | # trades |
|---|---|---|---|---|---|---|
| QQQ | **0.733 (FAIL, thr 1.0)** | **0.261 (FAIL, thr 0.25)** | 0.594 (pass) | 1.0 (pass) | 0.107 (pass) | 200 |
| SPY | **0.783 (FAIL, thr 1.0)** | 0.192 (pass) | 0.604 (pass) | 1.0 (pass) | 0.098 (pass) | 200 |

Full-sample Sharpe is well below 1.0 for both symbols despite the strong
low-vol-regime grid cells; the strategy is consistently profitable and
survives transaction costs and walk-forward (low parameter sensitivity too),
but simply doesn't clear the 1.0 Sharpe bar on the full 2010-2026 sample.
QQQ additionally slightly exceeds the 0.25 MDD threshold.

## Decision: REJECTED

Fails the primary Sharpe threshold (0.73/0.78 vs 1.0) on both QQQ and SPY;
QQQ also marginally exceeds max drawdown (0.261 vs 0.25). This is a "real
but modest" edge -- unlike the crypto (0/54) and many prior rejections in
this repo, TOM passes walk-forward, TC-survival, and has very low parameter
sensitivity, suggesting the effect itself is genuine and stable, just not
strong enough on its own to clear this repo's Sharpe bar. Crypto decisively
rejected across the whole grid.

Future revisit: combine with a trend filter (only take TOM entries when
price is above its own long SMA) or a vol-regime gate, since the grid shows
the edge concentrates in low-vol regimes (17/36 low vs 4/36 mid, 5/36 high)
-- adding that gate explicitly (rather than relying on regime-tercile
slicing after the fact) could push full-sample Sharpe above 1.0.
