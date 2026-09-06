# Standard Error Bands Trend-Continuation (narrowing-band filter)

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_seb_trend_continuation.py`
**KB id:** 2026-09-06-126

## Hypothesis

Standard Error Bands (SEB): middle = 3-period SMA of a 21-period linear
regression line of price; upper/lower = 3-period SMA of the regression line
+/- `se_mult` standard errors of the regression. Per QuantifiedStrategies.com's
stated interpretation, "bands narrowing while sloping = healthy trend
continuing; bands widening = trend weakening/reversing." Operationalized:
long entry when close breaks above upper band AND band width is narrower
than its own rolling average; exit on close < middle line, band-width
expansion past `expand_mult`x its rolling average, or a time-stop.

**Source:** https://www.quantifiedstrategies.com/standard-error-bands/ (browser_exec,
since web_extract failed with the DDGS search-only-backend error and
web_search itself errored on this iteration's query).

## Grid test (regression_window=[14,21,30] x expand_mult=[1.1,1.2,1.4], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 12/108 cells passed (equity 12/54, **crypto 0/54 decisive**)
- By vol regime: low 8/36, mid 3/36, high 1/36
- Best avg-config: regression_window=14, expand_mult=1.1, SPY avg Sharpe 1.31 across regimes

## Single-config validators (SPY, regression_window=14, expand_mult=1.1, full sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.864 | ≥ 1.0 |
| Max drawdown | PASS | 8.15% | ≤ 25% |
| TC survival (10bps, 37 trades) | PASS | net Sharpe 0.661 | ≥ 0.5 |
| Walk-forward (manual 4-split) | PASS (borderline) | 3/4 = 0.75 | ≥ 0.75 |
| Parameter sensitivity (9-cell SPY sweep) | **FAIL** | relative_std 0.656 | ≤ 0.5 |

QQQ sanity check at the same config: Sharpe **-0.172** (negative — does not
generalize even across the two equity tickers, despite QQQ having some
passing grid cells).

## Decision: **REJECT**

Full-sample Sharpe misses the 1.0 threshold, parameter sensitivity is high
(the grid-average Sharpe swings widely across regression_window x
expand_mult), and the QQQ cross-ticker sanity check is outright negative.
The grid's positive average on SPY appears driven by a handful of favorable
low-vol cells rather than a robust edge. Strategy/report kept as a record of
a rejected attempt.
