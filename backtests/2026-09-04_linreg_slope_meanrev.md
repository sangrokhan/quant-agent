# Linear Regression Slope Mean-Reversion (Negative-Slope Entry, Time-Stop Exit) — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_linreg_slope_meanrev.py`
**Source:** https://www.quantifiedstrategies.com/linear-regression-slope/
(web_search failed with a DDGS/Yahoo TLS connection error, fell back to
browser_exec)

## Hypothesis

Per QuantifiedStrategies' article: the rolling N-day linear regression
slope of price is a trend-strength/direction oscillator. Source's own SPY
backtest found a NEGATIVE-slope mean-reversion entry (bet a short-term
downtrend bounces) outperforms the positive-slope trend-following
variant, best at a fixed 9-day hold, though still lagging buy-and-hold
overall.

## Step 6 — Grid test summary

Grid: `slope_window` in {5,10} x `hold_days` in {5,9}, symbols {QQQ, SPY}
(equity) x {BTC/USDT, ETH/USDT} (crypto), vol_regime_splits=3.

- **total_cells:** 48, **passed_cells:** 8, **pass_fraction:** 0.167
- **by_asset_class:** equity 8/24, crypto 0/24
- **by_vol_regime:** low 8/16, mid 0/16, high 0/16
- **best_cell:** slope_window=5, hold_days=9, QQQ, low-vol tercile, Sharpe 2.963
- **worst_cell:** slope_window=5, hold_days=5, SPY, mid-vol tercile, Sharpe -0.087

Full-sample sweep (4 param combos x 2 symbols):

| Symbol | Params | Sharpe | MDD | Trades |
|---|---|---|---|---|
| QQQ | sw=5, hold=5 | 0.821 | 0.337 | 407 |
| QQQ | sw=5, hold=9 | 1.151 | 0.371 | 297 |
| QQQ | sw=10, hold=5 | 0.690 | 0.356 | 315 |
| QQQ | sw=10, hold=9 | 0.878 | 0.248 | 231 |
| SPY | sw=5, hold=5 | 0.760 | 0.358 | 391 |
| SPY | sw=5, hold=9 | 0.958 | 0.285 | 291 |
| SPY | sw=10, hold=5 | 0.649 | 0.253 | 293 |
| SPY | sw=10, hold=9 | 0.824 | 0.234 | 218 |

The one config that clears the 1.0 Sharpe threshold (QQQ, slope_window=5,
hold_days=9, Sharpe 1.151) fails max drawdown decisively (0.371 vs 0.25
budget, 48% over). No combo passes both Sharpe AND max drawdown
simultaneously on either symbol. Skipped remaining validator suite per
Step 7 minimum-subset guidance.

## Decision

**Rejected (all asset classes).** High trade frequency (this is a
frequent short-hold mean-reversion strategy, 200-400+ trades over the
sample) drives large drawdowns whenever a losing streak clusters; the only
Sharpe-passing config fails max drawdown by a wide margin. Crypto rejected
decisively (0/24 grid cells).
