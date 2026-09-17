# Backtest report: Ehlers RocketRSI Mean-Reversion (TASC May 2018)

**Hypothesis**: RocketRSI (SuperSmoothed momentum -> up/down-close
accumulation ratio -> Fisher Transform) produces sharper, more precise
oversold/overbought spikes than classic RSI; entering long on a spike
below -OBOSLevel should capture a mean-reversion snap-back.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2018/05/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: obos_level=[1.0,1.5,2.0], max_hold_days=[5,10,20]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3
- total_cells=108, passed_cells=17, pass_fraction=0.157
- by_asset_class: equity 16/54 (0.296), crypto 1/54 (0.019)
- by_vol_regime: low 14/36, mid 1/36, high 2/36
- best_cell: equity SPY low-vol, obos_level=1.0/max_hold_days=20, Sharpe 2.27 (narrow-slice artifact)

## Full-sample Sharpe sweep (all symbols x 9 configs)
| Symbol | best config | Sharpe |
|---|---|---|
| QQQ | obos_level=1.0, max_hold_days=20 | 0.757 |
| SPY | obos_level=1.0, max_hold_days=5 | 0.888 (overall best) |
| BTC/USDT | obos_level=1.0, max_hold_days=5 | 0.192 |
| ETH/USDT | obos_level=1.0, max_hold_days=5 | 0.097 |

No config on any symbol clears the 1.0 Sharpe threshold. Higher
obos_level (1.5, 2.0 -- closer to the source's own default of 2.0)
performs WORSE than lower thresholds, often going negative, suggesting
the source's default extreme-spike threshold is too rare/aggressive for
this daily-bar implementation to generate enough signal.

## Decision: REJECTED
Decisive rejection across all 4 symbols x 9 configs (36 full-sample
evaluations, zero passes). Best full-sample Sharpe 0.888 (SPY,
obos_level=1.0), still meaningfully below the 1.0 threshold. Grid
pass_fraction (0.157) is a low-vol-regime artifact that doesn't survive
full-sample evaluation. No further validators run given the decisive
Sharpe failure across the entire grid.
