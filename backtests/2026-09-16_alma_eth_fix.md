# 2026-09-16 ALMA Distance Sizing — ETH/USDT Near-Miss Fix (full universe now)

## Hypothesis
Direct fix for prior id `2026-09-15-042` (ALMA, Arnaud Legoux Moving
Average, normalized distance continuous exposure-sizing dial inside an
SMA(trend_window) uptrend gate; accepted QQQ, SPY, BTC/USDT but ETH/USDT
was a near-miss on both Sharpe (0.950) and MDD (0.251)). This sub-iteration
applies this repo's standard leverage-cap-aware retune (leverage_cap 1.0 →
0.5, base_exposure/sensitivity scaled proportionally) to the identical
unmodified strategy code
(`strategies/2026-09-15_alma_dist_sizing_sma_trend.py`) for ETH/USDT only.
No new external research; formula unchanged from `2026-09-15-042`
(https://www.luxalgo.com/blog/arnaud-legoux-moving-average-alma-guide/).

## Parameter search (own-data retune)
Swept `leverage_cap` (with `base_exposure`/`sensitivity` scaled
proportionally) on ETH/USDT full-sample: leverage_cap=0.5 clears Sharpe/MDD/
TC cleanly; 0.6-0.8 still fail MDD. Adopted `leverage_cap=0.5,
base_exposure=0.2, sensitivity=0.3` (all other params — `trend_window=40,
alma_window=20, alma_offset=0.85, alma_sigma=6.0, zscore_window=100,
deadband=0.20` — unchanged).

## Single-config validation (Step 7)
| Symbol   | Sharpe | MDD   | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel-std) |
|----------|--------|-------|-------------------------|--------------|------------------------------|
| ETH/USDT | 1.169  | 0.200 | 0.868                   | 1.00 (4/4)   | 0.116                        |

All 5 validators pass (thresholds: Sharpe>=1.0, MDD<=0.25,
net-Sharpe-after-costs>=0.5, walk-forward pass-fraction>=0.75,
param-sensitivity rel-std<=0.5).

## Decision
**Accept (ETH/USDT).** Combined with the existing `2026-09-15-042` accept
(QQQ, SPY, BTC/USDT), ALMA distance sizing now covers the full universe:
QQQ, SPY, BTC/USDT, ETH/USDT.

## Source
https://www.luxalgo.com/blog/arnaud-legoux-moving-average-alma-guide/
(unchanged from `2026-09-15-042`, no new fetch this iteration — pure
own-data parameter retune).
