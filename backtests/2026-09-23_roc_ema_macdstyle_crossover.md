# ROC EMA-of-ROC crossover (MACD-style smoothing applied to ROC), trend-gated (REJECTED)

**Hypothesis:** per timinsight.com's ROC guide (Strategy 4: Smoothed ROC
Crossover System, https://timinsight.com/price-rate-of-change-roc-guide-en),
apply MACD-style EMA smoothing directly to the raw ROC(12) line itself
(fast EMA span 12, slow EMA span 26 of the ROC series), trade the
crossover, long-only gated by close > SMA(200).

Strategy file: `strategies/2026-09-23_roc_ema_macdstyle_crossover.py`

## Step 6 grid summary (roc_period in [10,12] x fast_span in [8,12], equity QQQ/SPY + crypto BTC/USDT, vol_regime_splits=3)

- total_cells: 36, passed_cells: 4, **pass_fraction: 0.111**
- by_asset_class: equity 2/24, crypto 2/12
- by_vol_regime: low 3/12, mid 0/12, high 1/12 — edge nearly entirely confined to low-vol regime
- best_cell: roc_period=12, fast_span=12, QQQ, low-vol regime, Sharpe 1.862
- worst_cell: same params, QQQ, high-vol regime, Sharpe -0.860

## Step 7 single-config validation (best config: roc_period=12, fast_span=12, full sample 2019-01-01 to 2026-09-01)

| Symbol | Trades | Sharpe | MDD | TC-survival net Sharpe | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| SPY | 51 | 0.385 (FAIL) | 0.100 (PASS) | 0.242 (FAIL, thr 0.5) | 0.711 (FAIL, thr 0.5) |
| QQQ | 47 | 0.211 (FAIL) | 0.170 (PASS) | 0.126 (FAIL, thr 0.5) | 0.431 (PASS) |

Walk-forward not run (light workload, and the full-sample/TC-cost failures
already decisively disqualify the config).

## Decision: REJECTED

Full-sample Sharpe collapses on both symbols (0.385 SPY, 0.211 QQQ) versus
the promising-looking low-vol-tercile grid cells — the low-vol slice
(Sharpe up to 1.86) does not generalize to the unconditional full sample,
and both symbols fail net-of-cost Sharpe decisively. SPY also fails
parameter sensitivity (0.711 relative std). Grid pass_fraction of only
0.111, concentrated almost entirely in the low-vol regime (3/4 passing
cells), confirms this is a narrow, non-robust edge rather than a
broadly-working strategy.
