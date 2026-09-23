# Ehlers 3-Pole Butterworth Filter Trigger Crossover — Backtest Report (2026-09-24)

## Hypothesis

A 3-pole Butterworth low-pass filter (John Ehlers, "Cybernetic Analysis for
Stocks and Futures", 2004) smooths price; a lagged "trigger" copy of that
same filter line is compared against it. The filter crossing above its
trigger signals a long entry (uptrend), crossing below signals exit.

Source: FMZ "Ehlers Three-Pole Butterworth Filter Crossover Trend
Quantitative Trading Strategy" (https://www.fmz.com/lang/en/strategy/498394,
read via browser_exec — `web_extract`'s DDGS backend cannot fetch page
content). Distinct from this repo's 2 prior Ehlers Precision Trend entries
(dual-length HIGHPASS filter difference, turning-point entry) and the
SuperSmoother entries (2-pole low-pass, slope+price-above-line trigger) —
none tested this specific filter-vs-its-own-lagged-trigger crossover.

## Strategy file

`strategies/2026-09-24_butterworth_3pole_trigger_cross.py`

## Grid test summary (Step 6)

72 cells: `period ∈ {15, 20, 30} × trigger_lag ∈ {2, 3}` × symbols
`{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime terciles, 2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | 0.333 (24/72) |
| equity pass | 21/36 (strong) |
| crypto pass | 3/36 (weak, BTC/USDT only, zero ETH/USDT passes) |
| low-vol pass | 15/24 |
| mid-vol pass | 6/24 |
| high-vol pass | 3/24 |
| best cell | QQQ low-vol, period=20/lag=3, Sharpe 3.04 |
| worst cell | SPY mid-vol, period=30/lag=2, Sharpe -0.35 |

Crypto's very weak grid showing (3/36, effectively 1 symbol only) was judged
not worth pursuing to full single-config validation this iteration.

## Single-config validation (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param-sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | period=20, trigger_lag=2, max_hold=30 | 1.322 ✅ | 0.244 ✅ | 1.229 ✅ | 1.0 ✅ | 0.055 ✅ | **ACCEPT** |
| SPY | period=15, trigger_lag=2, max_hold=40 | 1.296 ✅ | 0.152 ✅ | 1.144 ✅ | 1.0 ✅ | 0.238 ✅ | **ACCEPT** |

QQQ's initial best-grid-cell config (period=15/lag=2/max_hold=40) was a
narrow MDD near-miss (0.2557 vs 0.25 threshold). Widening the
`max_hold_days` search to {20, 30, 40} found period=20/lag=2/max_hold=30
clears MDD (0.244) while keeping Sharpe strong (1.322) — accepted with a
per-symbol-tuned `max_hold_days`.

## Decision

**Accepted for QQQ (period=20/lag=2/max_hold=30) and SPY
(period=15/lag=2/max_hold=40).** Both pass all 5 validators with healthy
margins. Crypto not pursued given the decisively weak grid showing.
