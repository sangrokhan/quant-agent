# Vortex Crossover + ATR Fixed TP:SL Exit — Backtest Report

**Date:** 2026-09-24 | **id:** 2026-09-24-014

## Hypothesis
Per StrategyVerdict's "Vortex Indicator Strategy Backtest: the Crossover
That Actually Has an Edge (Conditionally)"
(https://strategyverdict.com/vortex-indicator-backtest/), a rigorous
6-axis backtest of the standard Vortex(14) crossover found the edge
concentrated on higher timeframes (4H/1D) and, distinctly, found a FIXED
TP:SL RATIO exit robustly profitable across ratios 1:1 to 1:5 (peak
1:1.5). This repo's 5 prior Vortex entries all used opposite-crossover,
ADX-gated trailing-stop, continuous-sizing, dual-confirmation, or
separation-convergence exits -- none used a fixed ATR-based TP:SL bracket.
Long-only adaptation of source's stop-and-reverse system per SAFETY.md.

## Strategy file
`strategies/2026-09-24_vortex_crossover_tpsl.py`

## Grid summary
`param_grid={vi_period:[10,14,21], tp_sl_ratio:[1.0,1.5,2.0], atr_mult:[1.0,1.5]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=216, passed=62, pass_fraction=0.287
- by_asset_class: equity 53/108 (49.1%), crypto 9/108 (8.3%)
- by_vol_regime: low 45/72 (62.5%), mid 7/72 (9.7%), high 10/72 (13.9%)
- best_cell: QQQ vi_period=14/tp_sl_ratio=2.0/atr_mult=1.0, low-vol Sharpe 3.05

## Single-config validators

### QQQ (vi_period=14, atr_mult=1.5, tp_sl_ratio=1.5)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.441 | >=1.0 | YES |
| Max drawdown | 21.3% | <=25% | YES |
| Transaction cost survival (158 trades) | net Sharpe 1.189 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.174 | <=0.5 | YES |

### SPY (vi_period=10, atr_mult=1.5, tp_sl_ratio=1.5)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.354 | >=1.0 | YES |
| Max drawdown | 15.1% | <=25% | YES |
| Transaction cost survival (147 trades) | net Sharpe 1.054 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.119 | <=0.5 | YES |

## Decision: ACCEPTED (equity: QQQ + SPY)

Crypto not pursued for full-sample validation -- the grid's best BTC/USDT
cell averages MDD ~37% and best ETH/USDT cell ~58-62% across vol-regime
slices, a decisive equity/crypto divide consistent with this repo's
general pattern for trend-crossover-with-tight-exit constructions.

Note: this is the highest-conviction acceptance this cron trigger --
both symbols pass every validator with meaningful margin, and the ~150
trades per symbol give much more statistical confidence than several of
this trigger's other accepted strategies (21-45 trades).

Source: https://strategyverdict.com/vortex-indicator-backtest/
