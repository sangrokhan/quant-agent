# Backtest Report: Stochastic Momentum Index (SMI) Oversold Crossover (2026-09-04)

**Hypothesis:** SMI (Blau smoothed stochastic) crossing above its signal
line after being below an oversold threshold (-40/-30) signals a
mean-reversion long entry; exit on the opposite crossover, hitting the
overbought extreme, or a time-stop. Source: Google AI-overview synthesis of
TradingView/QuantifiedStrategies SMI explainers
(https://www.google.com/search?q=Stochastic+Momentum+Index+SMI+trading+strategy+entry+exit+rules).

**Strategy file:** `strategies/2026-09-04_smi_oversold_crossover.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: oversold_threshold in [-30, -40], max_hold_days in [10, 15, 20];
symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 48, passed_cells: 0, pass_fraction: 0.0
by_asset_class: equity 0/36, crypto 0/12
by_vol_regime: low 0/12, mid 0/12, high 0/12, n/a 0/12
best_cell: SPY, high-vol, oversold=-30/max_hold=20 -> Sharpe 0.94 (still below 1.0 threshold)
worst_cell: QQQ, low-vol, oversold=-30/max_hold=10 -> Sharpe -0.71
```

## Verdict: **REJECTED**

Decisive rejection at the grid stage — 0 of 48 cells passed the
Sharpe>=1.0 AND MDD<=0.25 bar across the full parameter x symbol x
vol-regime grid; even the single best cell (SPY high-vol) only reached
Sharpe 0.94, still short of threshold. No slice of the grid (asset class or
vol regime) shows a working edge, so this is a clean fail, not a
near-miss worth deeper single-config validation (Step 7 skipped per
RESEARCH_LOOP.md Step 8 guidance — reject when Step 6 is already decisive).

Not recommending revisit with the same construction; if retried, would need
a fundamentally different entry filter (e.g. combine with a longer-term
trend gate like the accepted Gann HiLo strategy, id 2026-09-04-128) rather
than the raw oversold-crossover alone.
