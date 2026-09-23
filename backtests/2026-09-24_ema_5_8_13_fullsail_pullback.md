# 5-8-13 Fibonacci EMA Ribbon "Full Sail" Pullback — Backtest Report

**Date:** 2026-09-24 | **id:** 2026-09-24-015

## Hypothesis
Per Stockpathshala's "5 8 13 EMA Crossover Strategy: How It Works in
Trading?" (https://stockpathshala.com/5-8-13-ema-crossover-strategy/):
EMA(5)/EMA(8)/EMA(13) ribbon "Full Sail" alignment (EMA5>EMA8>EMA13)
signals bullish momentum; source's highest-probability entry is a
pullback to the EMA8 middle line while alignment holds, not the initial
crossover. Exit ("aggressive" rule per source) when EMA5 crosses back
below EMA8. First Fibonacci-ribbon (5/8/13) or Guppy-style multi-EMA
strategy in this repo.

## Grid summary
`param_grid={pullback_band_pct:[0.0,0.005,0.01], max_hold_days:[10,20,30]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=108, passed=37, pass_fraction=0.343
- by_asset_class: equity 28/54 (51.9%), crypto 9/54 (16.7%)
- by_vol_regime: low 27/36 (75.0%), mid 9/36 (25.0%), high 1/36 (2.8%)
- best_cell: QQQ pullback_band_pct=0.005/max_hold_days=20, low-vol Sharpe 2.65

## Single-config validators

### QQQ (pullback_band_pct=0.01, max_hold_days=10)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.156 | >=1.0 | YES |
| Max drawdown | 27.2% | <=25% | **NO** (near-miss) |
| Transaction cost survival | net Sharpe 0.917 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.104 | <=0.5 | YES |

### SPY (pullback_band_pct=0.005, max_hold_days=10)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.042 | >=1.0 | YES |
| Max drawdown | 11.8% | <=25% | YES |
| Transaction cost survival | net Sharpe 0.713 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.261 | <=0.5 | YES |

### BTC/USDT (pullback_band_pct=0.0, max_hold_days=10)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.253 | >=1.0 | YES |
| Max drawdown | 43.8% | <=25% | **NO** (decisive) |
| Transaction cost survival | net Sharpe 1.180 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.039 | <=0.5 | YES |

## Decision: ACCEPTED (SPY ONLY)

SPY passes all 5 validators cleanly. Both tried QQQ configs (max_hold=10
and 20) narrowly fail max drawdown (27.2%/28.7% vs 25% threshold) despite
strong Sharpe -- a genuine near-miss (a tighter stop-loss overlay or lower
pullback_band_pct might rescue it in a future iteration, but not accepted
as-is). BTC/USDT fails MDD decisively (43.8%) despite an attractive
Sharpe -- crypto not viable for this strategy without additional risk
controls.

Source: https://stockpathshala.com/5-8-13-ema-crossover-strategy/
