# Monthly Options Expiration Day Short (opex intraday short) — Backtest Report

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_opex_third_friday_short.py`
**Source:** https://www.quantifiedstrategies.com/a-rare-day-trading-strategy-for-the-short-side/ (QuantifiedStrategies.com)

## Hypothesis

Order imbalances on monthly options expiration days (third Friday of each
month) tend to produce weak price action after the opening auction.
Disclosed rule: short the market at the open on the third Friday, cover at
the close. Source's own QQQ backtest: 322 trades, 58% win rate, profit
factor 1.7, average gain 0.23%/trade, only 4% market exposure.

## Grid test summary (Step 6)

96 cells: `day_min∈{15,17} × day_max∈{21} × quarterly_only∈{True,False}` on
equity {QQQ,SPY} and crypto {BTC/USDT,ETH/USDT} (crypto has no
expiration-day analogue, tested as a control/comparison), 3 vol-regime
terciles, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.1875 (18/96)**
- by_asset_class: equity 10/48, crypto 8/48
- by_vol_regime: low 8/32, mid 6/32, high 4/32
- best_cell: day_min=15, day_max=21, quarterly_only=False, QQQ, mid-vol, Sharpe 1.81

## Single-config validation (Step 7) — best_cell params, full sample 2019-2026

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** 0.778 | **FAIL** 0.559 | ≥1.0 |
| Max drawdown | pass 5.4% | pass 4.4% | ≤25% |
| Transaction cost survival | pass 0.567 (88 trades) | **FAIL** 0.313 (88 trades) | ≥0.5 |
| Walk-forward (4 splits) | pass 0.75 | pass 0.75 | ≥0.75 |

## Interpretation

Both symbols fail full-sample Sharpe at the grid's own best_cell config
(mirroring the pattern seen repeatedly this cron trigger where a promising
regime-sliced grid statistic does not survive full-sample validation). SPY
additionally fails transaction-cost survival. The very low max drawdown
(4-5%) and modest trade count (88 short-only day-trades over ~7.7 years,
matching the source's own low-exposure framing) confirm the strategy is
low-risk but does not clear the Sharpe bar for acceptance in this repo.

## Decision: **REJECTED**

Full-sample Sharpe fails on both QQQ (0.778) and SPY (0.559); SPY also
fails transaction-cost survival.
