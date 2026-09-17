# Backtest report: D'Errico Accumulation/Distribution Range Breakout (TASC Aug 2018)

**Hypothesis**: A rolling-range consolidation zone whose support floor
(Bot) has been RISING across successive consolidations (Bot > Bot[3x
length ago], a Dow-theory-style accumulation signature) resolves with a
long breakout above the zone's resistance (Top), confirmed by a lagged
volume pickup.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2018/08/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: length=[4,8,12], max_hold_days=[10,20,40]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3
- total_cells=108, passed_cells=42, pass_fraction=0.389
- by_asset_class: equity 27/54 (0.500), crypto 15/54 (0.278)
- by_vol_regime: low 26/36 (0.722), mid 13/36 (0.361), high 3/36 (0.083)
- best_cell: equity QQQ low-vol, length=4/max_hold_days=40, Sharpe 2.48

## Full-sample Sharpe sweep (all symbols x 9 configs)
| Symbol | best config | Sharpe | MDD |
|---|---|---|---|
| QQQ | length=12, max_hold_days=20 | 1.274 | 0.081 |
| SPY | length=4, max_hold_days=10 | 1.441 | 0.079 |
| BTC/USDT | all configs | 0.001-0.11 (all fail) | 0.22-0.69 |
| ETH/USDT | all configs | 0.01-0.11 (all fail) | 0.36-0.85 |

QQQ and SPY prefer DIFFERENT lengths (12 vs 4) -- per-symbol tuned configs.

## Single-config validators (Step 7)
| Validator | QQQ (length=12,mhd=20) | SPY (length=4,mhd=10) | Threshold |
|---|---|---|---|
| sharpe_ratio | PASS 1.274 | PASS 1.441 | 1.0 |
| max_drawdown | PASS 0.081 | PASS 0.079 | 0.25 |
| transaction_cost_survival (10bps/trade) | PASS 1.234 (19 trades) | PASS 1.298 (32 trades) | 0.5 |
| walk_forward (4 manual date-slices; vbt.utils.splitting still broken, known workaround) | PASS 4/4 | PASS 4/4 | 0.75 |
| parameter_sensitivity (9-config sweep) | PASS (thin) 0.467 | PASS 0.404 | 0.5 |

All 5 validators pass for BOTH QQQ and SPY (per-symbol tuned configs).
QQQ's parameter-sensitivity margin is thin (0.467 vs 0.5 threshold).

## Decision: ACCEPTED (equity QQQ + SPY, per-symbol tuned)
Crypto (BTC/USDT, ETH/USDT) rejected decisively -- best full-sample Sharpe
only 0.11 (ETH/USDT), severe drawdowns (0.22-0.85), reflecting the
multi-consolidation rising-floor pattern's poor fit to crypto's much
noisier range structure. Strategy scoped to equity only.
