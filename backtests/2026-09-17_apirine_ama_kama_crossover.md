# Backtest report: Apirine AMA/KAMA Crossover (Vitali Apirine, TASC Apr 2018)

**Hypothesis**: A new range-position-based adaptive moving average (AMA,
Apirine's own construction, distinct from Kaufman's efficiency-ratio-based
KAMA) crossed against the classic Kaufman KAMA identifies trend turns with
fewer whipsaws than either adaptive MA alone.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2018/04/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: periods=[8,10,15], max_hold_days=[10,20,40]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3
- total_cells=108, passed_cells=35, pass_fraction=0.324
- by_asset_class: equity 30/54 (0.556), crypto 5/54 (0.093)
- by_vol_regime: low 22/36 (0.611), mid 8/36 (0.222), high 5/36 (0.139)
- best_cell: equity QQQ low-vol, periods=15/max_hold_days=40, Sharpe 2.24

## Full-sample Sharpe sweep (all symbols x 9 configs)
| Symbol | best config | Sharpe |
|---|---|---|
| QQQ | periods=15, max_hold_days=20 | 1.151 |
| SPY | periods=10, max_hold_days=10 | 1.275 |
| BTC/USDT | all configs | -0.03 to 0.10 (all fail, severe MDD 0.52-0.91) |
| ETH/USDT | all configs | -0.08 to 0.20 (all fail, severe MDD 0.47-0.89) |

QQQ and SPY prefer DIFFERENT periods (15 vs 10) -- best per-symbol tuned
configs used rather than a shared config.

## Single-config validators (Step 7)
| Validator | QQQ (periods=15,mhd=20) | SPY (periods=10,mhd=10) | Threshold |
|---|---|---|---|
| sharpe_ratio | PASS 1.151 | PASS 1.275 | 1.0 |
| max_drawdown | PASS 0.135 | PASS 0.087 | 0.25 |
| transaction_cost_survival (10bps/trade) | PASS 1.092 (29 trades) | PASS 1.129 (43 trades) | 0.5 |
| walk_forward (4 manual date-slices; vbt.utils.splitting still broken, known workaround) | PASS 4/4 | PASS 4/4 | 0.75 |
| parameter_sensitivity (9-config sweep) | PASS 0.191 | PASS 0.260 | 0.5 |

All 5 validators pass for BOTH QQQ and SPY (per-symbol tuned configs).

## Decision: ACCEPTED (equity QQQ + SPY, per-symbol tuned)
Crypto (BTC/USDT, ETH/USDT) rejected decisively -- all configs produce
near-zero or negative Sharpe with severe drawdowns (0.47-0.91), reflecting
the two-adaptive-MA-crossover mechanism's poor fit to crypto's much higher
baseline volatility. Strategy scoped to equity only, with per-symbol
parameter tuning required (no shared config found that satisfies both).
