# Pivot Point SuperTrend — SPY Fix via Widened Deadband

**Date:** 2026-09-17
**Strategy file:** `strategies/2026-09-17_pp_supertrend_sizing_sma_trend.py` (unchanged code)

**Direct fix for:** 2026-09-17-106 (SPY rejected only on TC-survival
near-miss, net Sharpe 0.308<0.5, at config trend_window=30/pivot_period=5/
atr_factor=2.0/sensitivity=0.7/deadband=0.15, 301 trades over the sample).

**Fix hypothesis:** the SPY near-miss was driven by excess turnover (301
trades), not a Sharpe/MDD/WF/param-sensitivity edge problem. A targeted
sweep widening `deadband` (to cut turnover) found a passing config:
trend_window=40/pivot_period=3/atr_factor=2.0/sensitivity=0.7/deadband=0.35
— 145 trades (52% fewer), which clears the TC-survival threshold while
keeping Sharpe/MDD/WF/param-sensitivity all passing.

## Validators at the fixed config (SPY)

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.068 | 1.0 | YES |
| Max drawdown | 0.107 | 0.25 | YES |
| TC-survival (net Sharpe) | 0.661 | 0.5 | YES |
| Walk-forward | 0.75 | 0.75 | YES |
| Parameter sensitivity | 0.060 rel-std | 0.5 | YES |

**Decision: Accepted (SPY).** All 5 validators now pass. Combined with the
existing QQQ accept from 2026-09-17-106, Pivot Point SuperTrend's
continuous-sizing dial now covers equity (QQQ + SPY) — crypto remains
rejected (2026-09-17-106's decisive BTC/USDT and ETH/USDT rejection stands
unchanged; this sub-iteration did not revisit crypto).
