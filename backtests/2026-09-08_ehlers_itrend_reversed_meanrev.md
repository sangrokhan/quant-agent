# Backtest Report: Ehlers Instantaneous Trendline (Reversed) Mean-Reversion

**Strategy file:** `strategies/2026-09-08_ehlers_itrend_reversed_meanrev.py`
**Date:** 2026-09-08

## Hypothesis

Per https://www.elitetrader.com/et/threads/john-ehlers-trading-strategy-the-instantaneous-trendline-backtest.374341/
(quantifiedstrategies.com backtest of Ehlers' Instantaneous Trendline
crossover system, Stocks & Commodities Jan 2006): the textbook trend-
following rule (long when ITrend crosses above its own lagged value)
performed "disastrous" on ES/SPY, but REVERSING the direction (long when
ITrend crosses below its own lag, i.e. treating the sell signal as a
contrarian buy) with a short dominant-cycle period (optimized to 2) turned
it into a strategy reportedly beating buy-and-hold (10.56% annual vs 7.72%,
65.71% win rate, 1009 trades since 1993, MDD 23.96% vs 56.47% b&h, excluding
costs/dividends). We implement the reversed rule with the standard 2-pole
recursive Ehlers Instantaneous Trendline formula and a max_hold_days
time-stop substituting for the source's undisclosed price-action exit.

## Grid test (Step 6)

`param_grid={"period": [2,5,10], "max_hold_days": [5,10]}`,
symbols equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01. 72 cells total.

- **pass_fraction: 17/72 (23.6%)** — much broader than most recent iterations
- by_asset_class: equity 17/36, crypto 0/36 (decisive fail)
- by_vol_regime: low 12/24, mid 3/24, high 2/24 (mostly low-vol, but not
  exclusively — some coverage in mid/high)
- best_cell: period=10, max_hold_days=5, QQQ, low-vol, Sharpe 2.08
- worst_cell: period=10, max_hold_days=5, BTC/USDT, mid-vol, Sharpe -0.04
  (crypto near flat/negative across the board, never a decisive blowup but
  never profitable either)

## Single-config validation (Step 7), config period=2/max_hold_days=10, QQQ, full sample 2019-2026

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.174 | 1.0 |
| Max drawdown | PASS | 18.2% | 25% |
| Transaction-cost survival (10bps/trade, 569 trades) | **FAIL (decisive)** | net Sharpe 0.434 | 0.5 |
| Walk-forward | ERROR (vectorbt `utils.splitting` attribute missing in installed version -- same dependency issue flagged in 2026-09-08-002; not evaluated) |
| Parameter sensitivity | PASS | relative_std 0.079 | 0.5 |

Parameter grid (Sharpe by config, full-sample QQQ) -- notably STABLE across
all 6 combos (1.03-1.21 range), unlike most rejected strategies this repo
has tested:
```
period=2,  mhd=5:  1.095
period=2,  mhd=10: 1.174
period=5,  mhd=5:  1.209
period=5,  mhd=10: 1.026
period=10, mhd=5:  0.978
period=10, mhd=10: 1.012
```

## Decision: REJECT

Sharpe, max drawdown, and parameter sensitivity all PASS comfortably (this
is one of the more robust-looking single-config results seen in this repo's
recent iterations), but the strategy trades 569 times over ~7.5 years on
QQQ alone (short period parameter -> very high signal frequency by
construction) and transaction-cost survival fails decisively: net Sharpe
after a modest 10bps/trade assumption collapses from 1.17 to 0.43, well
below the 0.5 threshold. This mirrors a recurring pattern in this repo's
knowledge base (e.g. 4-indicator confluence, gap+IBS+RSI swing) where a
short-holding-period mean-reversion signal that looks attractive gross
becomes uneconomical once realistic trading costs are applied. Grid also
confirms crypto is a decisive 0/36 (BTC/ETH near-flat-to-negative across
all cells) -- the source's "bullish drift bias" rationale for SPY does not
transfer to crypto. Worth flagging for a future revisit with either a
longer holding-period variant to cut trade frequency, or explicit net-of-
cost optimization in the grid search itself rather than only gross Sharpe.

Walk-forward validator errored again due to the same `vectorbt.utils.splitting`
dependency/API mismatch already flagged in 2026-09-08-002 -- not decisive to
this reject since TC-survival already failed independently, but worth
fixing in a future loop.
