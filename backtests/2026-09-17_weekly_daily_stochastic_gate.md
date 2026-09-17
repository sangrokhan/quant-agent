# Backtest report: Weekly & Daily Stochastic Regime-Gated Oversold Recovery (Vitali Apirine, TASC Sep 2018)

**Hypothesis**: A daily-only proxy for a weekly stochastic (length scaled
~5x: 70 vs classic daily 14) used as a trend-regime gate (StochW > midline
50 = weekly-proxy bullish) combined with a daily stochastic
oversold-recovery trigger (StochD crossing above 20) identifies
high-conviction long entries in a confirmed weekly uptrend.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2018/09/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: oversold=[20,30,40], max_hold_days=[10,20,40]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3
- total_cells=108, passed_cells=14, pass_fraction=0.130
- by_asset_class: equity 6/54 (0.111), crypto 8/54 (0.148)
- by_vol_regime: low 3/36, mid 11/36, high 0/36
- best_cell: crypto ETH/USDT mid-vol, oversold=30/max_hold_days=20, Sharpe 2.13 (narrow-slice artifact)

## Full-sample Sharpe sweep (all symbols x 9 configs)
| Symbol | best config | Sharpe |
|---|---|---|
| QQQ | oversold=40, max_hold_days=20 | -0.05 (best is still negative) |
| SPY | oversold=40, max_hold_days=10 | -0.099 (best is still negative) |
| BTC/USDT | oversold=30, max_hold_days=40 | 0.037 |
| ETH/USDT | oversold=30, max_hold_days=40 | 0.102 |

Equity full-sample Sharpe is NEGATIVE on the best config for both QQQ and
SPY -- this strategy actively loses money relative to being flat on equity,
not just failing to clear the threshold. Crypto is weakly positive but
far below the threshold.

## Decision: REJECTED
Decisive rejection across all 4 symbols x 9 configs (36 full-sample
evaluations, zero passes, best result 0.102). Equity results are notably
worse than typical rejections in this repo (negative Sharpe, not just
sub-threshold-positive), suggesting the weekly-proxy-gate + daily-oversold-
recovery combination is actively counterproductive on daily bars, not
merely weak. Grid pass_fraction (0.130) is a crypto-mid-vol narrow-slice
artifact. No further validators run given the decisive Sharpe failure.
