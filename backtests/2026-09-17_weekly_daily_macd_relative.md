# Backtest report: Weekly and Daily MACD Relative-Line Crossover (Vitali Apirine, TASC Dec 2017)

**Hypothesis**: A daily-only-data proxy for a weekly MACD (lengths scaled
~5x: 60/130 vs classic 12/26) combined additively with the classic daily
MACD into a "RelativeDailyLine" that crosses the weekly-proxy line signals
short-term daily momentum impulses strong enough to shift the combined
signal through the longer-term trend baseline.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2017/12/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: weekly_fast=[50,60,70] (weekly_slow stays at 130; only
  weekly_fast is swept -- small effect since 12/26 daily MACD dominates
  short-term crossover timing), max_hold_days=[10,20,40]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3
- total_cells=108, passed_cells=45, pass_fraction=0.417
- by_asset_class: equity 33/54 (0.611), crypto 12/54 (0.222)
- by_vol_regime: low 30/36 (0.833), mid 9/36 (0.25), high 6/36 (0.167)
- best_cell: equity QQQ low-vol, weekly_fast=50/max_hold_days=40, Sharpe 2.24

## Full-sample Sharpe sweep (all symbols x weekly_fast x max_hold_days)
weekly_fast has almost no effect within [50,60,70] (results identical
across that axis). Best max_hold_days=20 for both equity symbols:

| Symbol | max_hold_days=10 | =20 | =40 |
|---|---|---|---|
| QQQ | 0.944 | 1.266 (best) | 1.004 |
| SPY | 1.147 | 1.225 (best) | 0.952 |
| BTC/USDT | 0.10-0.18 (all fail) | | |
| ETH/USDT | 0.13-0.33 (all fail) | | |

## Single-config validators (Step 7) -- shared config weekly_fast=60, max_hold_days=20
| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| sharpe_ratio | PASS 1.266 | PASS 1.225 | 1.0 |
| max_drawdown | PASS 0.119 | PASS 0.073 | 0.25 |
| transaction_cost_survival (10bps/trade) | PASS 1.205 (28 trades) | PASS 1.157 (26 trades) | 0.5 |
| walk_forward (4 manual date-slices; vbt.utils.splitting still broken, known workaround) | PASS 4/4 | PASS 4/4 | 0.75 |
| parameter_sensitivity (9-config sweep) | PASS 0.131 | PASS 0.104 | 0.5 |

All 5 validators pass for BOTH QQQ and SPY using the SAME shared config.

## Decision: ACCEPTED (equity QQQ + SPY, shared config)
Crypto (BTC/USDT, ETH/USDT) rejected decisively -- best full-sample Sharpe
0.329 (ETH/USDT), well below threshold; only 12/54 crypto grid cells pass,
concentrated in low-vol tercile only. Strategy scoped to equity only.
