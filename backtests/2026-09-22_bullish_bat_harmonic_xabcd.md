# Backtest Report: Bullish Bat Harmonic Pattern (XABCD) (2026-09-22)

**Strategy file:** `strategies/2026-09-22_bullish_bat_harmonic_xabcd.py`
**KB id:** 2026-09-22-081
**Outcome: REJECTED (insufficient signal frequency)**

## Hypothesis
Scott Carney's Bat harmonic pattern is a 4-leg XABCD reversal defined by
specific Fibonacci ratios: AB retraces 0.382-0.50 of XA, BC retraces
0.382-0.886 of AB, and CD completes at 0.786-0.886 of XA (point D). Per
tradingstrategyguides.com's disclosed rules, a completed D point marks a
long-entry reversal signal.

## Grid test summary
- Grid: `swing_window` in {3,5} x `tolerance` in {0.08,0.12} x symbols
  {QQQ, SPY} x 3 vol-regime terciles = 24 cells.
- pass_fraction: 0.125 (3/24 pass) — **but this is a small-sample
  artifact**, not evidence of a real edge.

## Full-sample trade counts (2019-01-01 to 2026-09-01)
| Config | QQQ | SPY |
|---|---|---|
| sw=3, tol=0.08 | 0 | 2 |
| sw=3, tol=0.12 | 1 | 2 |
| sw=5, tol=0.08 | 0 | 0 |
| sw=5, tol=0.12 | 2 | 1 |

Every configuration produces 0-2 completed pattern signals over 7.5 years
of daily data — statistically meaningless sample size.

## Decision
**Reject** for insufficient signal frequency. The strict 3-ratio Fibonacci
matching requirement, even with an 8-12% tolerance band, is too restrictive
to fire often enough on daily equity bars to draw any conclusion. Full
validator suite skipped (Sharpe/MDD/walk-forward are meaningless on a
1-2-trade sample). Consistent with this repo's prior finding on the
related Gartley harmonic-pattern family (also signal-starved).

## Sources
- https://tradingstrategyguides.com/harmonic-bat-pattern-strategy/ (read
  via browser_exec fallback — web_search DDGS backend TLS-errored on 2
  consecutive queries this iteration).
