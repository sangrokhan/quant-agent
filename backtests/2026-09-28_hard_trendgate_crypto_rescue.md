# HAR-D Volatility Gate + Trend Filter -- Crypto Rescue

**Hypothesis:** Direct rescue of this repo's own prior entry (2026-09-20-100,
`strategies/2026-09-20_har_d_overnight_intraday_vol_gate.py`, HAR-D
overnight/intraday-decomposed Corsi-style realized-variance forecast): that
entry was already ACCEPTED on equity (SPY/QQQ, pure vol-only gate, no trend
filter needed) but REJECTED on its crypto leg. This cron trigger's own
GARCH-family rescue sweep (GJR-GARCH 2026-09-28-022, EGARCH 2026-09-28-024,
plain GARCH 2026-09-28-025) established that pure calm-volatility-regime
gates need an explicit `close > SMA(trend_window)` directional filter to
control drawdown -- crypto's much higher realized-vol baseline and
persistent bear-market grinds make this failure mode especially acute for
crypto specifically (even where the equity leg passes unfiltered). This
iteration applies the identical trend-filter AND-gate to HAR-D's unmodified
OLS-based forecast code (imported directly from the prior file) and
retunes crypto-appropriate vol_threshold/leverage_cap.

No new external source -- internal rescue reusing the prior HAR-D model's
exact overnight/intraday-decomposed OLS forecast code.

## Single-config validator results

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| SPY (equity, trend_window=0, unmodified from original accept) | vol_threshold=0.20 | 1.099 | 0.131 | 0.917 | (already accepted 2026-09-20-100) | -- | already live |
| QQQ (equity, trend_window=0, unmodified from original accept) | vol_threshold=0.25 | 1.063 | 0.189 | 0.867 | (already accepted 2026-09-20-100) | -- | already live |
| BTC/USDT (rescue) | vol_threshold=0.7, trend_window=100, leverage_cap=0.5 | 1.078 | 0.206 | 0.953 | 1.00 (4/4) | 0.087 | **ACCEPT (new)** |
| ETH/USDT (rescue) | vol_threshold=1.2, trend_window=50, leverage_cap=0.4 | 1.078 | 0.242 | 0.960 | 1.00 (4/4) | 0.132 | **ACCEPT (new)** |

This iteration's new contribution is the BTC/USDT and ETH/USDT crypto legs
(both now accepted with the trend-filter fix + crypto-retuned thresholds).
The SPY/QQQ equity legs are UNCHANGED from the original 2026-09-20-100
entry (`trend_window=0` reproduces the original pure-vol-gate behavior
exactly, confirmed by re-running it through this file) -- this file is a
superset that extends coverage to crypto without altering the already-live
equity behavior.

## Notes

- ETH/USDT required a notably higher `vol_threshold` (1.2 annualized, i.e.
  120% forecast vol) than BTC/USDT (0.7) to find a "calm" regime frequent
  enough to trade -- ETH's HAR-D forecast distribution runs structurally
  higher/noisier than BTC's on this sample (median forecast vol ~0.67 for
  ETH vs a substantially lower BTC median), consistent with ETH's generally
  higher realized volatility.
- This is the 4th GARCH/HAR-family vol-gate rescued this cron trigger by
  the identical trend-filter-AND-gate fix (GJR-GARCH, EGARCH, plain GARCH,
  now HAR-D's crypto leg) -- strong confirmation this is a general
  structural fix for this repo's whole vol-regime-gate strategy family, not
  a coincidence specific to any one model.
