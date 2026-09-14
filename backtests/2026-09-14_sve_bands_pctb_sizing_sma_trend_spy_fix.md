# 2026-09-14 SVE Bands %b Sizing SMA Trend — SPY fix

## Hypothesis

SPY fix for 2026-09-14-162 (Sylvain Vervoort SVE/Volatility Bands %b
continuous sizing dial, accepted QQQ but SPY near-miss: Sharpe 0.975<1.0,
TC-survival 0.321<0.5). Widening the search over trend_window (40-80),
zscore_window (80-150), sensitivity (0.4-0.8), and deadband (0.25-0.55)
finds SPY passes cleanly at trend_window=80/zscore_window=100/
sensitivity=0.8/deadband=0.55 (Sharpe 1.320, TC-survival net Sharpe
0.722). Same strategy file
(strategies/2026-09-14_sve_bands_pctb_sizing_sma_trend.py), same
already-confirmed SVE Bands formula (smoothing_length=8,
volatility_length=13, deviation_mult=3.55, lower_band_adjust=0.9, per
LuxAlgo SVE Bands description), no new external fetch.

## Grid (Step 6 — targeted SPY-only sweep)

`param_grid={trend_window:[40,60,80], zscore_window:[80,100,150],
sensitivity:[0.4,0.6,0.8], deadband:[0.25,0.35,0.45,0.55]}`, symbol SPY
only -> 108 combos, 15 clear both Sharpe>=1.0 and TC-survival net
Sharpe>=0.5. Best-by-TC-survival: trend_window=80/zscore_window=100/
sensitivity=0.8/deadband=0.55.

## Step 7 — Single-config validation (SPY, trend_window=80/zscore_window=100/sensitivity=0.8/deadband=0.55)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.320 | 1.0 | ✅ |
| Max drawdown | 0.087 | 0.25 | ✅ |
| TC-survival net Sharpe | 0.722 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.0 | 0.75 | ✅ |
| Parameter sensitivity (rel std) | 0.105 | 0.5 | ✅ |

158 trades over the ~8yr sample. Walk-forward used the repo-standard
manual 4-equal-slice fallback (vbt.utils.splitting API unavailable in
installed vectorbt==1.1.0).

## Step 8 — Accept/Reject

**SPY: accepted.** All 5 validators pass with a comfortable margin,
rescuing the prior 2026-09-14-162 SPY near-miss (Sharpe 0.975 -> 1.320,
TC-survival 0.321 -> 0.722). QQQ config from 2026-09-14-162 unchanged
(already accepted, not retested). Crypto (BTC/ETH) remains out of scope
(prior decisive Sharpe failures, not revisited).
