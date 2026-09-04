# Backtest Report: WaveTrend (WT1/WT2) Signal-Line Crossover (2026-09-04)

**Hypothesis:** The WaveTrend oscillator (WT1 = smoothed CCI-like channel
index, WT2 = its 4-period SMA signal line) generates a long entry when WT1
crosses above WT2 while both are in deep oversold territory (WT1 <=
oversold_threshold, e.g. -50/-60); exit on WT1 crossing back below WT2, WT1
rising into overbought (+60), or a max_hold_days time-stop. Source:
StrategyQuant/LazyBear WaveTrend codebase explainer
(https://strategyquant.com/codebase/wavetrend-wt/). First WaveTrend
strategy tried in this repo -- distinct from CCI/Stochastic/StochRSI
already tested (WT1 is a double-smoothed CCI-like construct crossed against
its own SMA signal line, MACD-style dual-line crossover rather than a raw
threshold rule).

**Strategy file:** `strategies/2026-09-04_wavetrend_signalline_crossover.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: channel_len[9,10,14], avg_len[12,21], oversold_threshold[-50.0,-60.0];
symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 96, passed_cells: 9, pass_fraction: 0.094
by_asset_class: equity 9/72, crypto 0/24
by_vol_regime: low 1/24, mid 6/24, high 2/24
best_cell: QQQ, mid-vol, channel_len=9/avg_len=12/oversold=-50.0 -> Sharpe 1.738
worst_cell: SPY, mid-vol, channel_len=10/avg_len=21/oversold=-50.0 -> Sharpe -1.072
```

## Step 7 single-config validators (channel_len=9, avg_len=12, oversold_threshold=-50.0, overbought=60.0, max_hold_days=15, full sample 2018-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ 0.675 (60 trades) | ❌ 0.171 (60 trades) | 1.0 |
| Max drawdown | ✅ 0.228 | ✅ 0.176 | 0.25 |
| Transaction cost survival (10bps/trade) | ✅ 0.576 | ❌ 0.071 | 0.5 |
| Walk-forward | ⚠️ skipped (grid already shows regime-dependence; full-sample already fails) | ⚠️ skipped | 0.75 |
| Parameter sensitivity (grid pass_fraction) | ❌ 9.4% pass rate across grid | -- | 0.5 |

## Verdict: **REJECTED**

Grid pass_fraction of 9.4% is decisive -- the strategy only clears the bar
in a narrow slice (mostly QQQ mid-vol) and fails completely on crypto (0/24)
and on low/high-vol regimes. Full-sample Sharpe confirmation also fails on
both equity symbols at the best grid config, so this isn't even a robust
"narrow but honest" accept case. The deep-oversold-crossover entry filter is
too restrictive (only 60 trades over 8+ years on QQQ) to generate a durable
edge net of costs.
