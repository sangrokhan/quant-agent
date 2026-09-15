# Backtest Report: ASI-minus-EMA Continuous Sizing — Crypto Leverage-Cap Fix

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-15_asi_diff_sizing_sma_trend.py` (unchanged)
**Knowledge base id:** 2026-09-16-102

## Hypothesis

Direct fix for prior id 2026-09-15-024 (Wilder Accumulative Swing
Index minus its own EMA, continuous sizing dial within an
SMA(trend_window) uptrend gate; accepted QQQ+SPY equity, but BTC/USDT
and ETH/USDT both decisively failed max-drawdown at leverage_cap=1.0
[0.398 and 0.324, both >0.25 threshold] despite passing Sharpe/TC-survival/
walk-forward/parameter-sensitivity). This sub-iteration applies this
repo's standard leverage-cap-aware retune (leverage_cap cut to 0.4,
base_exposure/sensitivity scaled proportionally) to the identical
unmodified ASI strategy code for crypto only. No new external research
this sub-iteration (same formula source as 2026-09-15-024:
https://fxopen.com/blog/en/accumulative-swing-index-definition-and-how-to-use-it/).

## Validation (crypto retune)

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.414 | 0.155 | 1.259 | 1.00 | 0.028 | PASS |
| ETH/USDT | 1.351 | 0.128 | 1.148 | 1.00 | 0.064 | PASS |

Both crypto symbols now pass all 5 validators at leverage_cap=0.4
(base_exposure=0.16, sensitivity=0.12), rescuing the prior decisive MDD
failure. QQQ/SPY equity configs unchanged from 2026-09-15-024.

## Outcome

**Accepted — full universe now** (QQQ, SPY from 2026-09-15-024 + BTC/USDT,
ETH/USDT newly accepted this sub-iteration). ASI-minus-EMA continuous
sizing dial now covers the complete asset universe.
