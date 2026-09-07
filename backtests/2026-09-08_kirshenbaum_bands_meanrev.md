# Backtest Report: Kirshenbaum Bands Mean Reversion (uptrend-filtered)

**Strategy file:** `strategies/2026-09-08_kirshenbaum_bands_meanrev.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Kirshenbaum Bands (Paul Kirshenbaum) place an EMA(period1) centerline with
bands offset by `no_sd_dev` standard errors of a rolling OLS linear-regression
fit of price over `period2` bars — distinct from Bollinger Bands (plain
rolling stdev) because it measures volatility *around the current trend*
rather than raw price dispersion. Hypothesis: a close dipping below the lower
Kirshenbaum band while the SMA200 uptrend filter is still intact is a
short-term overextension that reverts to the EMA centerline.

Sources:
- https://docs.motivewave.com/studies/k-l (exact formula: EMA centerline +/-
  noSdDev * standard error of linear regression, default period1=30,
  period2=20, noSdDev=1)
- https://www.tradingview.com/script/dBTwZawK-Kirshenbaum-Bands/ (indicator
  background/description)
- https://gocharting.com/features/community/scripts/2dde87f1-7adb-45c2-9380-41e41a0a8da4
  (trading-application notes: reversal signals at band touches)

First Kirshenbaum Bands strategy in this repo — distinct from the already-
rejected "Standard Error Bands" trend-continuation strategy (2026-09-06-126:
SMA-of-regression-line centerline, trades breakout ABOVE band, no EMA
centerline / no trend filter) and "Linear Regression Channel" breakout
(2026-09-04-141: raw OLS channel, no EMA/no SE-of-regression construction).

## Grid Test Summary (Step 6)

`param_grid={"no_sd_dev": [1.0, 1.5, 2.0], "max_hold_days": [5, 10]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **72 total cells, 4 passed (pass_fraction = 0.056)**
- By asset class: equity 4/36, crypto 0/36 (decisive crypto fail)
- By vol regime: low 2/24, mid 1/24, high 1/24 (no clean regime concentration)
- Best cell: `no_sd_dev=1.5, max_hold_days=5`, SPY low-vol, Sharpe 1.19
- Worst cell: `no_sd_dev=1.5, max_hold_days=10`, ETH/USDT high-vol, Sharpe -0.16

## Single-Config Validation (Step 7, best-cell config on SPY full sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.53 | 1.00 |
| Max drawdown | PASS | 9.9% | 25% |

Full-sample Sharpe decisively misses threshold even at the single grid cell
that looked best in isolation (a low-vol-tercile slice) — the edge does not
hold up over the whole sample. Given the decisive Sharpe fail plus the very
low overall grid pass fraction (5.6%) and total crypto washout, walk-forward
and parameter-sensitivity checks were skipped (workload=normal, but the
Sharpe fail alone is already decisive per RESEARCH_LOOP.md Step 7 guidance).

## Decision

**REJECTED.** Full-sample Sharpe fails on the single best-cell config; grid
pass fraction is low (4/72) with no clean asset-class or vol-regime
concentration to justify a narrower-scope accept. Crypto rejected decisively
(0/36).
