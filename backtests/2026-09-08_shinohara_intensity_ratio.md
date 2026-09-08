# Shinohara Intensity Ratio (SIR) Smoothed Strong/Weak Crossover — Backtest Report

**Date:** 2026-09-08 | **Strategy file:** `strategies/2026-09-08_shinohara_intensity_ratio.py` | **Outcome: REJECTED**

## Hypothesis
Per theforexgeek.com's Shinohara Intensity Ratio explainer (browser_exec
fallback — web_search DuckDuckGo errored with a TLS connection error on the
first query), Strong Ratio=(Close-Low)/(High-Low) and Weak Ratio=(High-
Close)/(High-Low) are per-bar intrabar strength ratios. Since these two
trivially sum to 1.0 per bar (not a market signal on their own), this repo
smooths each with a rolling SMA(sir_window) before comparing, consistent
with gocharting.com's framing of "significantly higher... sustained".
Source's rule: long when Strong Ratio crosses above Weak Ratio, exit on the
reverse cross.

Sources: https://gocharting.com/docs/charting/technical-indicator/momentum/shinohara-indicator ;
https://theforexgeek.com/shinohara-intensity-ratio-indicator (exact formula)

## Grid test (sir_window=[7,14,21] x max_hold_days=[20,30], QQQ/SPY equity + BTC-USDT/ETH-USDT crypto, vol_regime_splits=3, 2019-2026)

- 48 cells total (36 equity + 12 crypto attempted), 13 passed (pass_fraction 0.271)
- By asset class: equity 13/36, crypto 0/12
- **Bug found and fixed:** the initial grid run hit a `pandas.errors.DataError:
  No numeric types to aggregate` on crypto data, caused by using `pd.NA`
  (object-dtype sentinel) instead of `float("nan")` in the zero-range
  division guard, which silently upcast the whole Series to `object` dtype
  and broke `.rolling().mean()`. Fixed in the strategy file
  (`rng.replace(0, pd.NA)` -> `rng.replace(0, float("nan"))`). Post-fix
  direct full-sample check (sir_window=14, max_hold_days=30): BTC/USDT
  Sharpe 0.052, ETH/USDT Sharpe 0.220 -- confirms crypto genuinely fails,
  not just a data-shape artifact.
- By vol regime: low 10/12, mid 3/12, high 0/12
- Best cell: sir_window=14/max_hold_days=30, SPY low-vol, Sharpe 2.18
- Best avg-across-regime configs: SPY sw=14/mh=30 avg Sharpe 1.02; QQQ sw=21/mh=20 avg Sharpe 0.93

## Single-config validators (per-symbol best avg configs)

| Validator | QQQ (sw=21, mh=20) | SPY (sw=14, mh=30) | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.441 **FAIL** | 0.578 **FAIL** | >= 1.0 |
| Max Drawdown | 0.339 **FAIL** | 0.254 **FAIL** (barely) | <= 0.25 |
| TC survival (10bps, 70/88 trades) | 0.347 **FAIL** | 0.452 **FAIL** | >= 0.5 |
| Walk-forward (4-split manual) | 0.75 PASS | 0.75 PASS | >= 0.75 |
| Parameter sensitivity | 0.335 PASS | 0.431 PASS | <= 0.5 |
| Trade count | 70 | 88 | n/a (high frequency, drives TC drag) |

## Verdict
**REJECTED (decisive).** Both QQQ and SPY fail Sharpe, max drawdown, and
TC-survival at full sample despite legitimate trade counts (70-88) and
passing walk-forward/parameter-sensitivity. The grid's regime-split average
Sharpe (0.93-1.02) substantially overstates full-sample performance (0.44-
0.58) — another instance of the regime-average-vs-full-sample divergence
pattern seen in several recent iterations (e.g. KST 2026-09-08-047). High
trade frequency (70-88 trades) erodes the edge via transaction costs. The
underlying smoothed Strong/Weak crossover does not produce a robust signal
robust signal on either equity ticker; crypto (post-bug-fix) confirms
decisive rejection (BTC/USDT Sharpe 0.052, ETH/USDT 0.220).
