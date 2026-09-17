# Backtest report: CAM (Coordinated ADX and MACD) Trend Regime (Barbara Star, TASC Jan 2018)

**Hypothesis**: A 2x2 state machine ("CAM UP/DN/CT/PB") based on whether
ADX(10) is rising AND whether MACD(12,26) is rising jointly identifies
confirmed trend regimes ("CAM UP" = both rising) worth a long entry.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2018/01/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: ema_trend_window=[0,50,100] (0=disabled), max_hold_days=[10,20,40]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3
- total_cells=108, passed_cells=33, pass_fraction=0.306
- by_asset_class: equity 18/54 (0.333), crypto 15/54 (0.278)
- by_vol_regime: low 27/36 (0.75), mid 6/36 (0.167), high 0/36
- best_cell: equity QQQ low-vol, ema_trend_window=0/max_hold_days=10, Sharpe 2.64

## Full-sample Sharpe sweep
| Symbol | best config | Sharpe |
|---|---|---|
| QQQ | ema_trend_window=0, max_hold_days=10 | 1.047 (marginal pass) |
| SPY | all configs | 0.039 to 0.283 (all fail) |
| BTC/USDT | all configs | 0.21-0.24 (all fail) |
| ETH/USDT | all configs | 0.24-0.27 (all fail) |

Adding an EMA trend filter (ema_trend_window=50/100) HURT QQQ performance
(0.87-0.93 vs 1.05 with filter disabled) -- source's own suggestion to add
an EMA confirmation filter does not help here.

## Single-config validators (Step 7) -- QQQ, ema_trend_window=0, max_hold_days=10
| Validator | Result | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | PASS (marginal) | 1.047 | 1.0 |
| max_drawdown | PASS | 0.124 | 0.25 |
| transaction_cost_survival (10bps/trade, 165 trades) | PASS (thin) | 0.642 | 0.5 |
| walk_forward (4 manual date-slices; vbt.utils.splitting still broken, known workaround) | PASS | 4/4 | 0.75 |
| parameter_sensitivity (9-config sweep) | PASS | 0.078 | 0.5 |

All 5 validators pass, but the margin is thin: Sharpe 1.047 vs 1.0
threshold, and 165 trades (high turnover) drags the tx-cost-adjusted
Sharpe down to 0.642 vs a 0.5 threshold -- a slightly higher per-trade
cost assumption would flip this to reject.

## Decision: ACCEPTED (QQQ only, thin margin -- flag for future re-check)
SPY and crypto rejected decisively (Sharpe well under 1.0 on every config
tested). QQQ accept is real but fragile: high trade frequency (165 trades
over 7.5yr) makes it more transaction-cost-sensitive than most accepted
strategies in this repo (compare Four-Day Breakout's 27 trades, MACD
Relative-Line's ~27 trades). Future loops revisiting this idea should try
tightening entry (e.g. requiring N consecutive bars in CAM UP before entry)
to reduce whipsaw trade count.
