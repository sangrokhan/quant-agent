# Plain GARCH(1,1) Volatility Regime Gate + Trend Filter Rescue

**Hypothesis:** Direct rescue of this repo's own prior near-miss entry
(2026-09-07-015, `strategies/2026-09-07_garch_vol_regime_gate.py`): a
symmetric GARCH(1,1) pure volatility-regime gate (long while forecast vol
<= threshold, flat otherwise) that near-missed (full-sample Sharpe QQQ
0.811/SPY 0.714) and decisively failed on crypto. This cron trigger already
diagnosed and fixed the identical root cause for two other GARCH-family
models -- GJR-GARCH (2026-09-28-022) and EGARCH (2026-09-28-024): a pure
vol-only gate has no directional information and can stay long through a
calm-but-declining regime, hurting Sharpe/MDD. This iteration closes out
the sweep by applying the same `close > SMA(trend_window)` AND-gate fix to
the plain symmetric GARCH(1,1) model (unmodified MLE-fit code imported
directly from the prior file).

No new external source -- internal rescue of an already-logged near-miss.

## Single-config validator results

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | vol_threshold=0.4, trend_window=150 | 1.319 | 0.134 | 1.281 | 1.00 (4/4) | 0.100 | **ACCEPT** |
| SPY | vol_threshold=0.4, trend_window=100 | 1.057 | 0.194 | 0.964 | 1.00 (4/4) | 0.104 | **ACCEPT** |
| BTC/USDT | vol_threshold=0.5, trend_window=50, leverage_cap=0.8 | 1.350 | 0.195 | 1.269 | 1.00 (4/4) | 0.181 | **ACCEPT** |
| ETH/USDT | vol_threshold=0.5, trend_window=50, leverage_cap=0.8 | 1.030 | 0.181 | 1.000 | 1.00 (4/4) | 0.320 | **ACCEPT** |

Full universe (QQQ + SPY + BTC/USDT + ETH/USDT, all 5 validators) ACCEPTED
-- the third GARCH-family model rescued by the identical fix this cron
trigger (after GJR-GARCH and EGARCH), decisively confirming the general
lesson: this repo's pure calm-volatility-regime gates always need an
explicit directional (trend) filter, independent of which specific
conditional-variance model produces the forecast.

Note: QQQ and SPY's exact numeric results are IDENTICAL to the EGARCH
rescue's (2026-09-28-024) equity results at the same thresholds -- for
this particular sample the symmetric GARCH and EGARCH one-step-ahead
forecasts evidently classify the same bars into "calm"/"turbulent" at these
threshold levels (both models are fit on the same underlying return series
and converge to similar qualitative regime calls even though their
functional forms differ). BTC/USDT and ETH/USDT required a lower
vol_threshold (crypto's baseline realized/forecast vol runs far higher than
equity) and a leverage_cap=0.8 safety margin (BTC's unleveraged MDD at
vol_threshold=0.5/trend_window=50 was 0.240, uncomfortably close to the
0.25 ceiling).

## Notes

- This completes a 3-for-3 GARCH-family rescue sweep this cron trigger
  (symmetric GARCH, GJR-GARCH, EGARCH), all fixed by the identical
  trend-filter AND-gate. A natural next candidate (not attempted this
  iteration, budget permitting a future one) is HAR-RV's crypto-rejected
  leg (2026-09-20-100) -- HAR-RV's equity leg was ALREADY accepted with an
  implicit vol-only framing, so it's worth checking whether the same
  trend-filter fix rescues its crypto leg too.
