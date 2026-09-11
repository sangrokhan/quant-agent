# Backtest Report: RSMK (Relative Strength, Markos Katsanos) Signal-Line Crossover

**Strategy file:** `strategies/2026-09-12_rsmk_relative_strength_crossover.py` (REJECTED — kept as rejected-attempt record)
**Date:** 2026-09-12
**Source:** Markos Katsanos, TASC March 2020 Traders' Tips ("Relative Strength"), formula transcribed from https://www.tradingview.com/script/qhNCXBmL-Relative-Strength-RSMK-Perks/

## Hypothesis

`RSMK = EMA(MOM(log(Asset/Index), period), smooth) * 100`, `signalRSMK =
EMA(RSMK, signal_period)` (source defaults: period=90, smooth=3,
signal_period=20). RSMK crossing above its own signal line signals the
asset outperforming the chosen benchmark index -- a long entry, mirroring
the standard MACD/signal-line reading convention. Tested QQQ vs SPY
benchmark and SPY vs QQQ benchmark (equity); ETH/USDT vs BTC/USDT
benchmark (crypto). First RSMK-specific strategy in this repo.

## Step 6 — Grid test summary

Grid: `period` in [60,90,120] x `signal_period` in [10,20,30], equity
QQQ/SPY (cross-benchmarked against each other), crypto ETH/USDT (vs
BTC/USDT benchmark), vol_regime_splits=3 (81 cells: 54 equity + 27 crypto).

```
total_cells: 81, passed_cells: 11, pass_fraction: 0.136
by_asset_class: equity 11/54 passed; crypto 0/27 (decisive reject)
by_vol_regime:  low 9/27; mid 1/27; high 1/27
best_cell: period=60, signal_period=10, QQQ, low-vol, Sharpe=3.45
worst_cell: period=90, signal_period=30, QQQ, high-vol, Sharpe=-0.50
```

## Step 7 — Single-config validation (best grid config: period=60, smooth=3.0, signal_period=10, max_hold_days=30)

Full 2018-01-01..2026-09-01 sample:

| Metric | QQQ (vs SPY) | SPY (vs QQQ) | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.877 FAIL | 0.618 FAIL | >= 1.0 |
| Max Drawdown | 0.289 FAIL | 0.197 PASS | <= 0.25 |
| TC survival (10bps/trade) | 0.757 PASS | 0.470 FAIL | net Sharpe >= 0.5 |
| Walk-forward (4-split) | 1.00 PASS | 1.00 PASS | >= 0.75 |
| Param sensitivity (rel std) | 0.444 PASS | 0.165 PASS | <= 0.5 |

## Step 8 — Decision: **REJECT**

Both QQQ and SPY fail the primary Sharpe threshold (0.877/0.618 < 1.0);
QQQ additionally fails MDD (0.289 > 0.25) and SPY fails TC survival
(0.470 < 0.5). The strong low-vol-regime cell (Sharpe 3.45) does not
generalize to the full mixed-regime sample. Crypto rejected decisively
(0/27 grid cells, ETH vs BTC benchmark). The RSMK signal-line-crossover
construction, while conceptually distinct from prior relative-strength
strategies tested in this repo, does not clear the acceptance bar on
either tested benchmark pairing.
