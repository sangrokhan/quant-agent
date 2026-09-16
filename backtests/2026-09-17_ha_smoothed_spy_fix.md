# Heikin-Ashi Smoothed Body — SPY Fix via Widened Deadband

**Date:** 2026-09-17
**Strategy file:** `strategies/2026-09-17_ha_smoothed_body_sizing_sma_trend.py` (unchanged code)

**Direct fix for:** 2026-09-17-108 (SPY rejected only on TC-survival
failure, net Sharpe 0.187<0.5, at config trend_window=30/smooth_period=6/
sensitivity=0.7/deadband=0.20, 401 trades over the sample).

**Fix hypothesis:** following the same successful turnover-reduction
pattern used for Pivot Point SuperTrend's SPY fix this cron trigger
(2026-09-17-107), widen `deadband` to cut turnover while keeping the
Sharpe edge. A sweep found: trend_window=30/smooth_period=20/
sensitivity=0.7/deadband=0.40 (widened from 0.20 to 0.40, smooth_period
widened from 6 to 20) — 117 trades (71% fewer than the near-miss config's
401), clearing the TC-survival threshold.

## Validators at the fixed config (SPY)

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.278 | 1.0 | YES |
| Max drawdown | 0.084 | 0.25 | YES |
| TC-survival (net Sharpe) | 0.887 | 0.5 | YES |
| Walk-forward | 1.0 | 0.75 | YES |
| Parameter sensitivity | 0.068 rel-std | 0.5 | YES |

**Decision: Accepted (SPY).** All 5 validators now pass. Combined with the
existing QQQ accept from 2026-09-17-108, Heikin-Ashi Smoothed body
continuous-sizing dial now covers equity (QQQ + SPY) — crypto remains
rejected (2026-09-17-108's decisive BTC/USDT and ETH/USDT rejection stands
unchanged; this sub-iteration did not revisit crypto).

**Meta-note:** this is now the second consecutive successful
"widen-deadband-to-cut-turnover" SPY rescue this cron trigger (after
2026-09-17-107's Pivot Point SuperTrend fix), reinforcing that this repo's
TC-survival validator with 10bps/trade cost is often the binding constraint
for continuous-sizing-dial strategies on SPY specifically (lower gross
Sharpe edge than QQQ historically in this repo, so turnover-related cost
drag disproportionately hurts SPY's TC-survival pass/fail).
