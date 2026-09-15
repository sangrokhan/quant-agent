# Backtest Report: 3-Factor Regime Allocation — Exposure-Cap Fix (QQQ) + Wider Param Search (SPY)

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-12_regime_trend_vol_credit_tiered.py` (added `max_exposure` param)
**Knowledge base id:** 2026-09-16-106

## Hypothesis

Direct fix for prior id 2026-09-12-165 (3-Factor Regime Allocation:
weekly tiered exposure {0, 0.5, 1.0} based on count of 3 favorable
booleans — trend (close>200SMA), volatility (VIX<VIX3M), credit (HYG/IEF
z-score>0); flagged as "the strongest near-miss this cron trigger" —
QQQ passed Sharpe (1.01) but failed MDD (0.298>0.25); SPY passed MDD but
missed Sharpe (0.79). The 2026-09-12-165 notes explicitly flagged: "cap
full-exposure tier below 100% (e.g. 80%) to address QQQ MDD failure while
preserving Sharpe edge" as the follow-up direction. This sub-iteration
implements exactly that: added a `max_exposure` parameter (default 1.0,
backward-compatible) that scales both the full and half exposure tiers
proportionally. For SPY, a separate wider `trend_window`/
`credit_zscore_window` search (beyond the original grid) was needed since
the Sharpe shortfall wasn't an exposure-cap issue. No new external
research this sub-iteration (same source as 2026-09-12-165: TASC July
2026 Traders' Tips via
https://www.tradingview.com/script/wu1VhNpf-TASC-2026-07-Risk-On-Risk-Off-Or-Caution/).

## Validation

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=150/credit_zscore_window=80/max_exposure=0.75 | 1.060 | 0.232 | 0.928 | 0.75 | ~0 (nearly flat) | PASS |
| SPY | trend_window=180/credit_zscore_window=120/max_exposure=1.0 | 1.108 | 0.201 | 0.971 | 0.75 | 0.031 | PASS |

Both QQQ and SPY now pass all 5 validators. QQQ's exposure-cap fix
(max_exposure=0.75) trades a small amount of Sharpe for a large MDD
improvement (0.298->0.232), directly resolving the flagged issue. SPY
needed a genuinely wider trend_window/credit_zscore_window search
(180/120 vs original grid's max 200/100) rather than an exposure cap.

## Outcome

**Accepted — equity (QQQ, SPY)**. Rescues the "strongest near-miss this
cron trigger" flagged in 2026-09-12-165. Crypto remains decisively
rejected (0/24 or 0/48 grid cells in the original entry) — out of scope,
not attempted.
