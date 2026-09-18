# Backtest Report: Bullish Key Reversal Day (SPY, max_hold_days=24)

**Date:** 2026-09-18
**Status:** REJECTED (decisive)

## Hypothesis

Source: https://www.quantifiedstrategies.com/reversal-day-trading-strategy/

A Bullish Key Reversal Day (selling climax): today's low < yesterday's low
(fresh lower low) AND today's close > yesterday's high (full intraday
reversal). Source's own disclosed rule and GLD backtest reported an
optimal 24-day exit with average trade +2.02%, profit factor > 1.0
(bullish setup only -- bearish mirror setup underperformed and is
excluded here). Adapted long-only to any OHLC price_df.

## Step 6 grid summary (`grid_result_key_reversal_day.json`)

- param_grid: `max_hold_days` in [10, 24, 40]
- symbols: equity (QQQ, SPY), crypto (BTC/USDT, ETH/USDT)
- vol_regime_splits: 3
- **pass_fraction: 0.083 (3/36 cells)**
- by_asset_class: equity 3/18, crypto 0/18 (decisive crypto reject)
- by_vol_regime: low 3/12, mid 0/12, high 0/12
- best_cell: SPY, max_hold_days=24, low-vol regime, Sharpe 2.15
- worst_cell: SPY, max_hold_days=10, mid-vol regime, Sharpe -0.71

## Step 7 single-config validation (SPY, max_hold_days=24, full sample 2015-01-01 to 2026-09-01)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.164 | >= 1.0 |
| Max drawdown | **FAIL** | 0.336 | <= 0.25 |
| TC survival (10bps/trade, 42 trades) | **FAIL** | net Sharpe 0.122 | >= 0.5 |
| Walk-forward (4 splits) | pass (borderline) | 0.75 pass fraction | >= 0.75 |
| Parameter sensitivity (max_hold_days 10/24/40) | **FAIL** | rel_std 0.797 | <= 0.5 |

## Decision: REJECT (decisive)

Unlike the source's isolated GLD backtest (which reported profit factor
>1.0 for the bullish setup), this single-bar pattern does not hold up on
SPY/QQQ full-sample or on crypto at all. Only 1 of 5 validators passes
(walk-forward, and only just barely at the 0.75 threshold). The pattern
appears highly regime-narrow (only the isolated low-vol tercile shows a
strong Sharpe) and is not robust to the max_hold_days parameter (rel_std
0.80, nearly 2x the sensitivity of the already-marginal 123-pattern
rescue). No further rescue attempted this iteration given the decisive
multi-validator failure (unlike 2026-09-18-090/091's near-miss profile).

Left `strategies/2026-09-18_key_reversal_day.py` in place as a rejected-
attempt record.
