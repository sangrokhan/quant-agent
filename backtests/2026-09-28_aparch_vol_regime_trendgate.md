# Backtest Report: apARCH (Ding, Granger & Engle 1993) Free-Power Asymmetric Volatility Regime Gate + Trend Filter

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_aparch_vol_regime_trendgate.py`
**Status:** ACCEPTED (full universe: QQQ, SPY, BTC/USDT, ETH/USDT)

## Hypothesis

Per Ding, Granger & Engle (1993), formula confirmed via the `rugarch` R
package vignette (Section 2.2.5, apARCH -- same PDF already read this cron
trigger for the Component GARCH, TGARCH, and NAGARCH entries, fourth
distinct submodel consulted). Genuinely novel for this repo (0 prior
"apARCH"/"asymmetric power ARCH" hits):

    sigma_t^delta = omega + alpha*(|eps_{t-1}| - gamma*eps_{t-1})^delta + beta*sigma_{t-1}^delta

The key structural distinction: delta is a FREE Box-Cox power parameter
fit via MLE jointly with the other parameters (not fixed a priori like
every other GARCH-family variant this trigger -- TGARCH fixes delta=1,
GJR-GARCH/plain GARCH fix delta=2). Named after the Taylor (1986) effect
that absolute-return autocorrelation often exceeds squared-return
autocorrelation.

MLE diagnostic (QQQ, full-sample fit): the free-fitted delta converged to
~1.038 -- very close to TGARCH's fixed delta=1, empirically confirming the
Taylor-effect motivation for this data, though the fitted asymmetry
parameter gamma (~0.60) differs materially from TGARCH's separately-fit
gamma, so this is not merely a re-derivation of the earlier TGARCH result.

## Parameter tuning

- QQQ: vol_threshold_quantile=0.9, trend_window=150
- SPY: vol_threshold_quantile=0.8, trend_window=200
- BTC/USDT: vol_threshold_quantile=0.8, trend_window=50, leverage_cap=0.4
- ETH/USDT: vol_threshold_quantile=0.7, trend_window=50, leverage_cap=0.4

## Single-config validation (Step 7)

| Symbol | Sharpe | MDD | Net Sharpe (10bps, N trades) | Walk-forward (4-split) |
|---|---|---|---|---|
| QQQ | 1.349 (pass) | 0.160 (pass) | 1.279 (pass), 55 trades | 4/4 splits positive (pass) |
| SPY | 1.033 (pass) | 0.180 (pass) | 0.832 (pass), 99 trades | 4/4 splits positive (pass) |
| BTC/USDT (lev 0.4) | 1.512 (pass) | 0.207 (pass) | 1.175 (pass), 207 trades | 4/4 splits positive (pass) |
| ETH/USDT (lev 0.4) | 1.420 (pass) | 0.188 (pass) | 1.185 (pass), 201 trades | 4/4 splits positive (pass) |

Parameter sensitivity (QQQ, trend_window in [150,200,250] x
vol_threshold_quantile in [0.8,0.9]): relative_std = 0.106 (mean Sharpe
0.994, std 0.105), threshold 0.5. **PASS.**

Walk-forward used a manual 4-equal-chunk split (vectorbt's `RangeSplitter`
API broken in this repo per this cron trigger's now-standard workaround
note).

## Decision: ACCEPT (full universe)

All 4 symbols pass all 5 validators. 9th distinct GARCH/HAR/CARR-family
volatility model validated this cron trigger.
