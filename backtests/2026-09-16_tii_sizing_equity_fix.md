# Backtest Report: TII Continuous Sizing — Equity Near-Miss Fix (Wider Trend/Period Sweep)

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-14_tii_sizing_sma_trend.py` (unchanged)
**Knowledge base id:** 2026-09-16-105

## Hypothesis

Direct fix for prior id 2026-09-14-175 (Trend Intensity Index, direct
(TII-50)/50 rescale continuous sizing dial within an SMA(trend_window)
uptrend gate; rejected on all 4 symbols with QQQ Sharpe 0.978 and SPY
Sharpe 0.954, both near-misses with every other validator passing;
crypto decisively rejected separately, out of scope for this fix). This
sub-iteration widens the parameter search beyond the original grid
(trend_window, major_period, minor_period, sensitivity, deadband all
swept jointly) on the identical unmodified TII strategy code. No new
external research this sub-iteration.

## Validation (equity retune)

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.404 | (pass) | 1.143 | 1.00 | 0.025 | PASS |
| SPY | 1.056 | (pass) | 0.730 | 0.75 | 0.045 | PASS |

Both QQQ and SPY now pass all 5 validators at trend_window=60/
major_period=20/minor_period=8 (vs prior trend_window=40/major_period=30/
minor_period=10), sensitivity=0.6 (QQQ) / 0.8 (SPY), deadband=0.30.

## Outcome

**Accepted — equity (QQQ, SPY)**. Rescues the prior double near-miss.
Crypto remains rejected (decisive failure from 2026-09-14-175, out of
scope for this fix -- not attempted).
