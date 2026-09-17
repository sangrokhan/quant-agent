# Backtest report: Soldier Gap Reversal (TASC Oct 2017)

**Hypothesis**: D'Ambrosio & Star's modified "Soldier" reversal candle
(TASC Oct 2017 "A Candlestick Strategy With Soldiers And Crows") --
single-bar reversal after a 2-bar downtrend + specific gap/close geometry
relative to the prior bar -- signals a tradeable long reversal.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2017/10/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: exit_sma_window=[3,5,8], max_hold_days=[5,10,20]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3 (low/mid/high realized-vol terciles)
- total_cells=108, passed_cells=26, pass_fraction=0.241
- by_asset_class: equity 17/54 (0.315), crypto 9/54 (0.167)
- by_vol_regime: low 4/36, mid 22/36, high 0/36 (edge concentrated entirely
  in mid-vol regime; zero pass in high-vol)
- best_cell: crypto BTC/USDT mid-vol, exit_sma_window=8/max_hold_days=5, Sharpe 1.34

## Full-sample single-config validators (Step 7)
Sharpe ratio (min_sharpe=1.0) computed on full-period returns for every
grid config, all asset classes:

| Symbol | exit_sma_window | max_hold_days | Sharpe | Pass |
|---|---|---|---|---|
| QQQ | 3/5/8 | 5/10/20 | 0.15-0.55 | all FAIL |
| SPY | 3/5/8 | 5/10/20 | 0.51-0.79 | all FAIL |
| BTC/USDT | 3/5/8 | 5/10/20 | 0.17-0.21 | all FAIL |
| ETH/USDT | 3/5/8 | 5/10/20 | 0.04-0.07 | all FAIL |

Best full-sample Sharpe overall: SPY exit_sma_window=5, max_hold_days=10/20
(Sharpe 0.789) -- still well below the 1.0 threshold.

## Decision: REJECTED
Grid pass_fraction (0.241) is a mid-vol-regime artifact -- 22/26 passing
cells are from the "mid" vol tercile, and the best cell's Sharpe (1.34) does
not survive to full-sample evaluation on any symbol/config (max full-sample
Sharpe observed: 0.789 on SPY). No config passes the Sharpe validator at the
1.0 threshold; walk-forward/tx-cost/param-sensitivity not run given the
decisive Sharpe failure across every cell (workload=max but no point running
further validators on an already-failed primary gate).
