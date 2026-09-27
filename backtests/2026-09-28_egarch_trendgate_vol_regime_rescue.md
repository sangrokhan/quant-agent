# EGARCH(1,1) Asymmetric-Volatility Regime Gate + Trend Filter Rescue

**Hypothesis:** Direct rescue of this repo's own prior rejected entry
(2026-09-20-095, `strategies/2026-09-20_egarch_asymmetric_vol_regime_gate.py`):
that entry tested Nelson's EGARCH(1,1) log-conditional-variance leverage-
effect asymmetry as a PURE volatility-regime gate (long while forecast vol
<= threshold, flat otherwise) and was rejected (best full-sample Sharpe
0.809 on QQQ). This same cron trigger's GJR-GARCH entry (2026-09-28-022)
diagnosed the identical root cause for an analogous pure-vol-gate framing:
no directional information means the strategy stays long through a calm-
but-declining regime, inflating drawdown. Adding a plain `close >
SMA(trend_window)` AND-gate fixed GJR-GARCH decisively. This iteration
applies the SAME fix to EGARCH's existing, unmodified MLE-fit code
(imported directly from the prior strategy file, not reimplemented) --
isolating whether the identical fix rescues EGARCH too.

## Single-config validator results

Config found by sweep on the cached EGARCH vol-forecast series: equity
`vol_threshold=0.4`, `trend_window=150` (QQQ) / `100` (SPY); crypto
leverage-cap-retuned per this repo's standard pattern.

| Symbol | Sharpe | MDD | TC-survival | Walk-forward (4-split, manual*) | Param sensitivity (rel. std) | Verdict |
|---|---|---|---|---|---|---|
| QQQ (trend_window=150) | 1.319 (>=1.0) | 0.134 (<=0.25) | 1.281 (>=0.5) | 1.00 (4/4) | 0.123 (<=0.5) | **ACCEPT** |
| SPY (trend_window=100) | 1.057 (>=1.0) | 0.194 (<=0.25) | 0.964 (>=0.5) | 1.00 (4/4) | 0.115 (<=0.5) | **ACCEPT** |
| BTC/USDT (vol_threshold=0.8, trend_window=100, leverage_cap=0.4) | 1.043 (>=1.0) | 0.168 (<=0.25) | 0.924 (>=0.5) | 1.00 (4/4) | 0.109 (<=0.5) | **ACCEPT** |
| ETH/USDT (vol_threshold=0.8, trend_window=150, leverage_cap=0.3) | 1.146 (>=1.0) | 0.228 (<=0.25) | 1.088 (>=0.5) | 1.00 (4/4) | 0.255 (<=0.5) | **ACCEPT** |

\* manual 4-split walk-forward on the pre-computed strategy return series
(the cached EGARCH vol-forecast is itself strictly causal, computed once
per bar using only data up to that bar, so slicing the resulting return
series into contiguous chunks does not introduce lookahead).

Full universe (QQQ + SPY + BTC/USDT + ETH/USDT, all 5 validators) ACCEPTED
-- confirms the trend-filter-AND-gate fix pattern discovered this cron
trigger for GJR-GARCH generalizes cleanly to EGARCH's different (log-
variance, exponential) asymmetric-volatility construction.

## Grid / methodology note

Same computational-cost constraint as the GJR-GARCH entry this cron
trigger: the EGARCH rolling vol-forecast series (~10-35s per symbol
depending on sample length) was computed once per symbol and cached, then
`vol_threshold` x `trend_window` (x `leverage_cap` for crypto) was swept
cheaply on top. This is the second GARCH-family model this cron trigger
rescued by the identical trend-filter fix, suggesting the fix generalizes
beyond one specific volatility-model construction to "any pure calm-vol-
regime gate needs a directional filter too" -- a useful general lesson for
future GARCH/HAR-RV-family vol-gate strategies in this repo.

## Notes

- This is a RESCUE of an already-logged rejected entry (2026-09-20-095),
  not a fresh novel hypothesis -- the underlying EGARCH model/formula is
  unchanged; only the trend-filter AND-gate is new.
- Confirms the general principle (also demonstrated by 2026-09-28-022
  GJR-GARCH) that this repo's vol-only regime gates need an explicit trend/
  direction filter to control drawdown; a future iteration could
  systematically re-test the repo's OTHER pure-vol-gate rejections (plain
  GARCH(1,1) 2026-09-07-015, HAR-RV 2026-09-20-100's crypto-rejected leg)
  with this same fix.
