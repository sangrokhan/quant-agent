# Backtest Report: RVI Signal-Line Crossover, Zero-Regime Confirmed (2026-09-04)

**Hypothesis:** Relative Vigor Index (RVI) -- v_t = (Close-Open)/(High-Low),
RVI = SMA(v_t, n), Signal = SMA(RVI, m) -- crossing above its signal line
while RVI is in a positive (uptrend-biased) regime signals a long entry;
exit on the opposite crossover, RVI dropping to/below zero, or a
max_hold_days time-stop. Source:
https://trendsandbreakouts.com/relative-vigor-index. First RVI strategy in
this repo -- distinct from Balance of Power (similar close-vs-open concept,
already tested, but no double-smoothed signal-line crossover).

**Strategy file:** `strategies/2026-09-04_rvi_signalline_zeroregime.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: rvi_period[7,10,14], signal_period[3,4,6], max_hold_days[10,20];
symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 144, passed_cells: 43, pass_fraction: 0.299
by_asset_class: equity 43/108, crypto 0/36
by_vol_regime: low 34/36, mid 8/36, high 1/36
best_cell: SPY, low-vol, rvi_period=14/signal_period=4/max_hold_days=20 -> Sharpe 2.017
worst_cell: QQQ, high-vol, rvi_period=10/signal_period=3/max_hold_days=10 -> Sharpe -1.010
```

## Step 7 single-config validators (rvi_period=14, signal_period=4, max_hold_days=20, full sample 2018-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ 0.660 (444 trades) | ❌ 0.759 (424 trades) | 1.0 |
| Max drawdown | ✅ 0.159 | ✅ 0.143 | 0.25 |
| Transaction cost survival (10bps/trade) | ❌ 0.028 | ❌ 0.028 | 0.5 |
| Walk-forward | ⚠️ skipped (full-sample fails decisively) | ⚠️ skipped | 0.75 |
| Parameter sensitivity (grid pass_fraction) | ❌ 29.9% pass rate across grid | -- | 0.5 |

## Verdict: **REJECTED**

Grid pass_fraction 29.9% is concentrated almost entirely in low-vol equity
cells (34/36 low-vol vs 8/36 mid, 1/36 high) and 0/36 on crypto. The
signal-line crossover fires very frequently (~424-444 round trips over
8 years -- roughly one every ~9 trading days), producing a strategy that
fails transaction-cost survival decisively on both symbols even before the
raw Sharpe miss. High trade frequency from the double-SMA-smoothed
crossover is the key failure mode here, distinct from the prior two
rejections' narrow-regime issues.
