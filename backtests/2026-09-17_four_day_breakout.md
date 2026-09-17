# Backtest report: Four-Day Breakout Swing (Ken Calhoun, TASC Nov 2017)

**Hypothesis**: Four consecutive green (close>open) daily candles mark
strong sustained momentum; entering on a subsequent breakout above the
4-bar high captures continuation swing moves.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2017/11/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: trail_window=[5,10,20], max_hold_days=[10,20,40]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3
- total_cells=108, passed_cells=22, pass_fraction=0.204
- by_asset_class: equity 21/54 (0.389), crypto 1/54 (0.019)
- by_vol_regime: low 19/36 (0.528), mid 0/36, high 3/36 (0.083)
- best_cell: equity SPY low-vol, trail_window=20/max_hold_days=40, Sharpe 2.88

## Full-sample Sharpe sweep (all symbols x 9 configs)
| Symbol | best Sharpe (config) |
|---|---|
| QQQ | 1.425 (trail_window=20, max_hold_days=40) |
| SPY | 0.891 (trail_window=20, max_hold_days=40) -- near-miss, below 1.0 threshold |
| BTC/USDT | 0.090 (all configs weak) |
| ETH/USDT | 0.092 (all configs weak, several negative) |

## Single-config validators (Step 7) -- QQQ, trail_window=20, max_hold_days=40
| Validator | Result | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | PASS | 1.425 | 1.0 |
| max_drawdown | PASS | 0.163 | 0.25 |
| transaction_cost_survival (10bps/trade, 27 trades) | PASS | 1.382 | 0.5 |
| walk_forward (4 manual date-slices; vbt.utils.splitting still broken, same known workaround as prior iterations) | PASS | 4/4 splits positive | 0.75 |
| parameter_sensitivity (9-config QQQ sweep) | PASS | relative_std 0.322 | 0.5 |

All 5 validators pass for QQQ.

## Decision: ACCEPTED (QQQ only)
SPY is a near-miss (full-sample Sharpe 0.891, below the 1.0 threshold) --
not accepted. Crypto (BTC/USDT, ETH/USDT) rejected decisively (Sharpe
<0.1 on all configs, only 1/54 grid cells pass, MDD 0.30-0.68). Strategy
kept in `strategies/` scoped to QQQ only; SPY/crypto use is not supported
by this validation and should not be assumed to generalize.
