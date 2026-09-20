# Backtest Report: Cumulative CaseyC% Mean Reversion

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_cumulative_caseyc_meanrev.py`
**Source:** https://statoasis.com/overfit/research/caseyc-oscillator-a-smarter-mean-reversion-strategy-for-sp500-traders (Ali Casey / StatOasis, visited via `browser_exec`)

## Hypothesis

CaseyC% ranks N-period momentum within a trailing window via percentile
rank (close to this repo's already-accepted Cesar Alvarez PercentRank(ROC),
id=2026-09-04-121). The source's "Cumulative CaseyC%" variant sums the
last 3 daily CaseyC% readings before thresholding -- a stronger,
noise-smoothed mean-reversion filter distinct from the plain single-day
PercentRank(ROC) construction already tested.

## Grid Test Summary (Step 6)

`param_grid={"entry_threshold": [20,30,50], "max_hold_days": [7,10,15]}`,
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Total cells:** 108, **passed:** 17, **pass_fraction:** 0.157
- **By asset class:** equity 14/54 (0.259), crypto 3/54 (0.056)
- **By vol regime:** low 10/36 (0.278), mid 6/36 (0.167), high 1/36 (0.028)
- **Best cell:** equity/SPY, low-vol, `entry_threshold=50, max_hold_days=7`,
  Sharpe 2.55
- Best full-sample-averaged equity config: `entry_threshold=50.0,
  max_hold_days=7` (avg equity Sharpe 1.13)

## Single-Config Validation (Step 7) — `entry_threshold=50.0, max_hold_days=7`

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd (4-split) | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.325 (FAIL) | 0.276 (FAIL) | 0.239 (FAIL) | 0.75 (PASS) | 2.226 (FAIL, wildly unstable) |
| SPY | 0.994 (FAIL, thr 1.0, essentially at the line) | 0.094 (PASS) | 0.826 (PASS) | 1.00 (PASS) | 0.645 (FAIL) |
| BTC/USDT | 0.430 (FAIL) | 0.449 (FAIL) | 0.398 (FAIL) | 0.75 (PASS) | 0.222 (PASS) |

## Decision (Step 8): **REJECTED**

SPY's full-period Sharpe (0.994) is essentially at the 1.0 threshold, but
the parameter-sensitivity check fails decisively (relative std 0.645 vs
0.5 threshold), and QQQ's own parameter-sensitivity blows up entirely
(relative std 2.23 -- some (entry_threshold, max_hold_days) combinations
produce near-zero or even negative Sharpe on QQQ, meaning the config
that happens to work well is fragile/overfit-looking rather than robust).
Crypto fails cleanly on both symbols (Sharpe and MDD). This is not a
strategy to accept even though SPY's headline number looks close -- the
grid and sensitivity checks both point to instability across the
threshold/hold-period choices, which is exactly the failure mode the
parameter-sensitivity validator exists to catch.
