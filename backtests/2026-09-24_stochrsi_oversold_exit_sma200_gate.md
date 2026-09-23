# StochRSI Oversold-Exit Entry + SMA(200) Trend Gate — Backtest Report (REJECTED)

**Date:** 2026-09-24 | **id:** 2026-09-24-016

## Hypothesis
Per CoinQuant's "Stochastic RSI on Crypto: What the Backtest Data Actually
Shows" (https://www.coinquant.ai/blog/stochastic-rsi-on-crypto-what-the-backtest-data-actually-shows):
a plain StochRSI(14,14,3,3) system (long on %K crossing above 20, exit on
%K crossing below 80) lost money on BTC despite a 59.9% win rate because
it kept buying oversold dips inside downtrends. Source's own suggested
fix: gate entries with a close > SMA(200) trend filter. Tested that exact
fix on QQQ, SPY, BTC/USDT.

## Grid summary
`param_grid={trend_window:[100,150,200], oversold_level:[15.0,20.0,25.0], max_hold_days:[15,30]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=216, passed=74, pass_fraction=0.343
- by_asset_class: equity 38/108 (35.2%), crypto 36/108 (33.3%)
- by_vol_regime: low 58/72 (80.6%), mid 16/72 (22.2%), high 0/72 (0.0%)
- best_cell: ETH/USDT trend_window=100/oversold_level=25.0/max_hold_days=15, mid-vol Sharpe 2.53

## Single-config validators

### BTC/USDT (trend_window=150, oversold_level=25.0, max_hold_days=15)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.022 | >=1.0 | YES |
| Max drawdown | 45.2% | <=25% | **NO** |
| Transaction cost survival (371 trades) | net Sharpe 0.781 | >=0.5 | YES |
| Walk-forward | 3/4 positive (0.75) | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.109 | <=0.5 | YES |

### SPY (trend_window=100, oversold_level=15.0, max_hold_days=30)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.694 | >=1.0 | **NO** |
| Max drawdown | 14.8% | <=25% | YES |
| Transaction cost survival (433 trades) | net Sharpe -0.042 | >=0.5 | **NO** |
| Walk-forward | 3/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.347 | <=0.5 | YES |

### QQQ (trend_window=150, oversold_level=20.0, max_hold_days=30)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.632 | >=1.0 | **NO** |
| Max drawdown | 21.3% | <=25% | YES |
| Transaction cost survival (409 trades) | net Sharpe 0.054 | >=0.5 | **NO** |
| Walk-forward | 3/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.159 | <=0.5 | YES |

## Decision: REJECTED (all symbols)

The SMA(200) trend-gate fix did not fully solve the source's documented
problem: on BTC it merely traded Sharpe for MDD (still-too-high 45.2%
MDD), and on equities the sheer trade frequency (400+ trades over ~7.7yr,
roughly 1 every 5 trading days) makes the strategy fee-sensitive enough
that transaction costs erase the edge (SPY net Sharpe actually turns
negative). A genuinely different fix (e.g. tightening oversold_level
further, or adding a minimum-holding-period between re-entries to reduce
overtrading) might work but is out of scope for this iteration.

Source: https://www.coinquant.ai/blog/stochastic-rsi-on-crypto-what-the-backtest-data-actually-shows
