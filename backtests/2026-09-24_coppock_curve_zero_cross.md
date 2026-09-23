# Coppock Curve Zero-Line Crossover — Backtest Report (REJECTED)

**Date:** 2026-09-24 | **id:** 2026-09-24-012

## Hypothesis
Per QuantifiedStrategies.com's "Coppock Curve Strategy: A Simple Long-Term
Market Timing Indicator"
(https://quantifiedstrategies.substack.com/p/coppock-curve-strategy-a-simple-long):
Coppock = WMA(wma_period) of (ROC(roc_long)+ROC(roc_short)) on close; buy
on cross above zero, sell on cross below zero. Source's own monthly-S&P500
backtest since 1960: 13 trades, 100% win ratio, CAGR 6.5% vs buy-hold 7.5%,
MDD -30% vs buy-hold -55% (a risk-adjusted-return story, not an absolute-
Sharpe-beats-1.0 story). Converted to daily-bar trading-day-equivalent
lookbacks (~21 trading days/month) for this repo's data.

## Grid summary
`param_grid={roc_long:[252,294,336], roc_short:[189,231,273], wma_period:[147,210]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2016-01-01..2026-09-01.

- total_cells=216, passed=44, pass_fraction=0.204
- by_asset_class: equity 44/108 (40.7%), crypto 0/108 (0.0%, decisive crypto reject)
- by_vol_regime: low 36/72 (50.0%), mid 8/72 (11.1%), high 0/72 (0.0%)
- best_cell: SPY roc_long=252/roc_short=273/wma_period=147, low-vol Sharpe 2.27

## Single-config validators

### QQQ (roc_long=294, roc_short=231, wma_period=147)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.889 | >=1.0 | NO |
| Max drawdown | 32.8% | <=25% | NO |
| Transaction cost survival (2 trades) | net Sharpe 0.888 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.026 | <=0.5 | YES |

### SPY (roc_long=252, roc_short=189, wma_period=147)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.795 | >=1.0 | NO |
| Max drawdown | 34.1% | <=25% | NO |
| Transaction cost survival (2 trades) | net Sharpe 0.794 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.043 | <=0.5 | YES |

## Decision: REJECTED (both QQQ and SPY)

Both configs fail Sharpe ratio AND max drawdown on the full 2016-2026
sample. With only 2 full-sample round trips (this indicator is a slow
long-term regime filter, not a frequent trading signal, per the source's
own description) the strategy stayed long through 2022's drawdown and
lagged buy-and-hold significantly in absolute risk-adjusted terms even
though the grid's sliced-window best cells looked attractive in isolation
(low-vol tercile Sharpe >2). This is a caution about over-trusting
sliced-grid Sharpe for very-low-trade-count strategies without a
full-sample sanity check (same lesson noted in prior id 2026-09-24-010's
BTC zero-trade caveat). Crypto is decisively rejected (0/108 grid cells).

Source: https://quantifiedstrategies.substack.com/p/coppock-curve-strategy-a-simple-long
