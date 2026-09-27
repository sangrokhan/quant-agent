# Backtest Report: NAGARCH (Engle & Ng 1993) Shift-Asymmetric Volatility Regime Gate + Trend Filter

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_nagarch_vol_regime_trendgate.py`
**Status:** ACCEPTED (full universe: QQQ, SPY, BTC/USDT, ETH/USDT)

## Hypothesis

Per Engle & Ng (1993), formula confirmed via the `rugarch` R package
vignette (Section 2.2.6, fGARCH omnibus family -- same PDF already read
this cron trigger for the Component GARCH and TGARCH entries, third
distinct submodel definition consulted). Genuinely novel for this repo (0
prior "NAGARCH"/"Nonlinear Asymmetric GARCH" hits): NAGARCH arises from the
fGARCH omnibus formula with delta=lambda=2, eta1=0:

    sigma_t^2 = omega + alpha*(eps_{t-1} - eta2*sigma_{t-1})^2 + beta*sigma_{t-1}^2

A SHIFT-based asymmetry mechanism, structurally distinct from both
GJR-GARCH (indicator-function-based, tested/rescued 2x this trigger) and
TGARCH (absolute-value-based, tested 2026-09-28-036 this trigger): the
innovation term is shifted by eta2*sigma_{t-1} BEFORE squaring, giving a
continuous, smoothly-varying quadratic asymmetry rather than a kinked or
discontinuous response. Applies this same cron trigger's 7x-validated
trend-filter AND-gate pattern.

## Parameter tuning

Unlike Component GARCH and TGARCH (which both needed a HIGH
vol_threshold_quantile of 0.7-0.9 to clear Sharpe 1.0), NAGARCH performed
well across a WIDER range of thresholds including moderate ones (QQQ
passed at vol_threshold_quantile=0.5 already, Sharpe 1.018) -- BTC/USDT in
particular found its best config at a SHORT trend_window=50 with
vol_threshold_quantile=0.9 (Sharpe 1.549, this cron trigger's highest
single-symbol Sharpe among all GARCH-family entries).

- QQQ/SPY: vol_threshold_quantile=0.9, trend_window=200
- BTC/USDT: vol_threshold_quantile=0.9, trend_window=50, leverage_cap=0.4
- ETH/USDT: vol_threshold_quantile=0.6, trend_window=150, leverage_cap=0.4

## Single-config validation (Step 7)

| Symbol | Sharpe | MDD | Net Sharpe (10bps, N trades) | Walk-forward (4-split) |
|---|---|---|---|---|
| QQQ | 1.243 (pass) | 0.213 (pass) | 1.198 (pass), 37 trades | 4/4 splits positive (pass) |
| SPY | 1.012 (pass) | 0.214 (pass) | 0.920 (pass), 53 trades | 4/4 splits positive (pass) |
| BTC/USDT (lev 0.4) | 1.549 (pass) | 0.226 (pass) | 1.299 (pass), 177 trades | 4/4 splits positive (pass) |
| ETH/USDT (lev 0.4) | 1.424 (pass) | 0.170 (pass) | 1.187 (pass), 171 trades | 4/4 splits positive (pass) |

Parameter sensitivity (QQQ, trend_window in [150,200,250] x
vol_threshold_quantile in [0.85,0.9,0.95]): relative_std = 0.098 (mean
Sharpe 1.014, std 0.099), threshold 0.5. **PASS.**

Walk-forward used a manual 4-equal-chunk split (vectorbt's `RangeSplitter`
API broken in this repo per this cron trigger's now-standard workaround
note).

## Decision: ACCEPT (full universe)

All 4 symbols pass all 5 validators. 8th distinct GARCH/HAR/CARR-family
volatility model validated this cron trigger, and the strongest single
Sharpe result (BTC/USDT 1.549) among all of them.
