# Backtest Report: KST (Know Sure Thing) Signal-Line Crossover Momentum

**Strategy file:** `strategies/2026-09-08_kst_signal_line_crossover_momentum.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Per Investopedia's "Understanding the Know Sure Thing (KST) Oscillator"
(https://www.investopedia.com/terms/k/know-sure-thing-kst.asp), Martin
Pring's KST composite (weighted sum of four smoothed multi-period ROC
terms) generates trading signals when the KST line crosses its 9-period
signal-line SMA. We implemented the long-only bullish-crossover version
with a `max_hold_days` time-stop backstop, on QQQ/SPY (equity) and
BTC/USDT, ETH/USDT (crypto).

First Know Sure Thing / Pring composite-ROC entry in this repo (zero prior
matches for "KST"/"Know Sure Thing" in `strategies_index.jsonl`).

## Step 6 — Grid test summary

Grid: `signal_window` in {9, 14} x `max_hold_days` in {15, 20, 30}, across
QQQ/SPY (equity) and BTC/USDT, ETH/USDT (crypto), 3 vol-regime terciles
(low/mid/high), 2019-01-01 to 2026-09-01. 72 cells total.

- **pass_fraction: 0.167** (12/72 cells)
- **by_asset_class:** equity 12/36 passed; crypto 0/36 passed (decisive fail)
- **by_vol_regime:** low 12/24 passed; mid 0/24; high 0/24 — momentum edge
  concentrated exclusively in the low-vol tercile
- **best_cell:** QQQ, signal_window=14, max_hold_days=15, low-vol regime,
  Sharpe 2.31
- **worst_cell:** SPY, signal_window=9, max_hold_days=15, mid-vol regime,
  Sharpe -0.33

## Step 7 — Standard validators (best config: QQQ, signal_window=14, max_hold_days=15, full sample 2019-2026)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.697 | >= 1.0 |
| Max drawdown | PASS | 0.208 | <= 0.25 |
| Transaction cost survival (10bps/trade, 46 trades) | PASS | net Sharpe 0.630 | >= 0.5 |
| Walk-forward (4 equal slices, manual fallback) | PASS | 1.0 (4/4 slices positive) | >= 0.75 |
| Parameter sensitivity (6-cell neighborhood) | PASS | relative std 0.116 | <= 0.5 |

## Decision: REJECT

Full-sample Sharpe (0.697) fails the 1.0 threshold. The grid's strong
best-cell Sharpe (2.31) is a low-vol-tercile-only artifact — the strategy's
edge does not survive across the mid/high vol regimes or full sample. Crypto
rejected decisively (0/36). Consistent with prior VWAP/momentum-composite
near-misses in this repo where full-sample performance is diluted by
mid/high-vol regime chop despite promising low-vol subsets.
