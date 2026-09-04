# Backtest Report: Qstick Moving-Average-Confirmation Crossover

**Strategy file:** `strategies/2026-09-04_qstick_ma_confirmation.py`
**Hypothesis id:** 2026-09-04-136
**Source:** https://technicalresources.in/how-to-trade-using-the-qstick-indicator/

## Hypothesis

Qstick (Tushar Chande): SMA of (close - open), measures candle-body-
direction momentum. Per the source's "Moving Average Confirmation
Strategy": buy when Qstick crosses above its own moving average AND stays
positive; sell/exit on the mirror condition (Qstick crosses below its own
MA AND turns negative), or a max_hold_days time-stop as a backstop.

## Single-config validators (SPY, qstick_window=14, signal_window=8, max_hold_days=40 -- Step 6 grid's best low-vol cell config)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full period) | ❌ | 0.401 | ≥ 1.0 |
| max_drawdown | ❌ | 0.256 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 53 trades) | ❌ | net Sharpe 0.333 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` still broken in this install) | ❌ | 2/4 splits positive Sharpe | ≥ 0.75 pass fraction |
| parameter_sensitivity | ❌ (borderline) | relative std 0.525 (8-combo grid) | ≤ 0.5 |

## Step 6 grid summary

`param_grid={qstick_window:[8,14], signal_window:[8,14], max_hold_days:[20,40]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
96 cells total.

- **pass_fraction:** 0.198 (19/96)
- **by_asset_class:** equity 19/48 passed (40%); crypto 0/48 passed (0%)
- **by_vol_regime:** low 16/32; mid 3/32; high 0/32
- **best_cell:** qstick_window=14, signal_window=8, max_hold_days=40, SPY, low-vol regime, Sharpe 3.08
- **worst_cell:** qstick_window=8, signal_window=8, max_hold_days=20, QQQ, high-vol regime, Sharpe -0.71

## Decision: REJECT (decisive)

All 5 validators fail on the full-period single-config run using the
grid's best-cell parameters -- the strong low-vol-tercile Sharpe (3.08)
does not generalize outside that narrow slice at all. This is a clean,
decisive rejection (unlike some recent near-misses): every validator
misses its threshold, including walk-forward at only 2/4 positive splits.
Candle-body-direction momentum (open-close spread smoothing) does not
appear to carry a robust standalone edge on daily equity/crypto bars in
this test setup.
