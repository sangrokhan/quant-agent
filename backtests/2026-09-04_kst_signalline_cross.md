# Know Sure Thing (KST) Signal-Line Cross Near Zero — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_kst_signalline_cross.py`
**Source:** https://www.quantifiedstrategies.com/kst-oscillator/ (specific
numeric backtest rule/code paywalled members-only; web_search failed with
a DDGS/Yahoo TLS connection error, fell back to browser_exec)

## Hypothesis

Martin Pring's KST (weighted sum of 4 SMA-smoothed ROC values, standard
periods 10/15/20/30 weighted x1/x2/x3/x4) crossing above its 9-period SMA
signal line while at/below the zero centerline (oversold-momentum
recovery) signals a long entry; exit on the opposite signal-line cross.

## Step 6 — Grid test summary

Grid: `signal_period` in {9,15} x `centerline_threshold` in {0.0,10.0},
symbols {QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto),
vol_regime_splits=3.

- **total_cells:** 48, **passed_cells:** 9, **pass_fraction:** 0.1875
- **by_asset_class:** equity 9/24, crypto 0/24
- **by_vol_regime:** low 8/16, mid 0/16, high 1/16
- **best_cell:** signal_period=9, centerline_threshold=0.0, QQQ, low-vol tercile, Sharpe 2.346
- **worst_cell:** signal_period=15, centerline_threshold=10.0, SPY, mid-vol tercile, Sharpe -0.719

Full-sample sweep (4 param combos x 2 symbols):

| Symbol | Params | Sharpe | MDD | Trades |
|---|---|---|---|---|
| QQQ | sp=9, ct=0.0 | 0.854 | 0.236 | 54 |
| QQQ | sp=9, ct=10.0 | 0.900 | 0.227 | 64 |
| QQQ | sp=15, ct=0.0 | 0.968 | 0.200 | 45 |
| QQQ | sp=15, ct=10.0 | 0.937 | 0.244 | 57 |
| SPY | sp=9, ct=0.0 | 0.560 | 0.172 | 48 |
| SPY | sp=9, ct=10.0 | 0.652 | 0.180 | 56 |
| SPY | sp=15, ct=0.0 | 0.579 | 0.196 | 42 |
| SPY | sp=15, ct=10.0 | 0.572 | 0.217 | 52 |

All 8 full-sample results are below the 1.0 Sharpe threshold, though QQQ
at signal_period=15/centerline_threshold=0.0 is a near-miss (0.968).
Skipped remaining validator suite per Step 7 minimum-subset guidance since
no config clears the threshold decisively enough to warrant full
validation.

## Decision

**Rejected (all asset classes).** Best full-sample Sharpe is 0.968 (QQQ,
signal_period=15, centerline_threshold=0.0) — a near-miss but does not
clear the 1.0 threshold. Grid pass_fraction 0.1875 (9/48), concentrated in
the low-vol tercile. Crypto rejected decisively (0/24 grid cells). Worth
revisiting: the near-miss QQQ config with a slightly wider centerline
threshold or a shorter ROC-period variant of KST.
