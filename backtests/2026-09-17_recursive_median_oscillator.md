# Backtest report: Ehlers Recursive Median Oscillator Zero-Cross (TASC Mar 2018)

**Hypothesis**: A 2-stage Ehlers filter (5-bar rolling median smoothed by a
cycle-period-derived EMA, then highpass-filtered to strip slow trend
components) produces a near-zero-lag oscillator whose zero-crossings mark
tradeable momentum turns.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2018/03/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: hp_period=[20,30,45], max_hold_days=[10,20,40]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3
- total_cells=108, passed_cells=22, pass_fraction=0.204
- by_asset_class: equity 20/54 (0.370), crypto 2/54 (0.037)
- by_vol_regime: low 12/36, mid 7/36, high 3/36
- best_cell: crypto BTC/USDT high-vol, hp_period=20/max_hold_days=20, Sharpe 1.71 (narrow-slice artifact)

## Full-sample Sharpe sweep (all symbols x 9 configs)
| Symbol | best Sharpe (config) |
|---|---|
| QQQ | 0.788 (hp_period=20, max_hold_days=20) |
| SPY | 0.871 (hp_period=30, max_hold_days=10) -- overall best, still below threshold |
| BTC/USDT | 0.270 (all configs weak) |
| ETH/USDT | 0.309 (all configs weak) |

No config on any symbol clears the 1.0 Sharpe threshold. Max drawdowns are
also elevated for equity (0.14-0.33) relative to most accepted strategies
in this repo, and crypto MDD is severe (0.34-0.69).

## Decision: REJECTED
Decisive rejection across all 4 symbols x 9 configs (36 full-sample
evaluations, zero passes). Grid pass_fraction (0.204) is a narrow-slice
artifact concentrated in crypto high-vol regime, which does not survive to
full-sample evaluation. No further validators run given the decisive
Sharpe failure across the entire grid.
