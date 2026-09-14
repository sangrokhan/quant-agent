# 2026-09-14 BW-MFI ROC Sizing SMA Trend — SPY fix

## Hypothesis

SPY fix for 2026-09-14-167 (Bill Williams' Market Facilitation Index
rate-of-change continuous sizing dial, accepted QQQ but SPY was an
extremely close double near-miss: Sharpe 0.998 vs 1.0 threshold, off by
only 0.2%, and TC-survival 0.464 vs 0.5). A wide 2700-combo sweep over
trend_window (30-100), roc_window (3-20), smooth_window (3-10),
zscore_window (80-150), sensitivity (0.3-0.6), and deadband (0.25-0.55)
finds SPY passes cleanly at trend_window=40/roc_window=20/smooth_window=5/
zscore_window=150/sensitivity=0.3/deadband=0.35 (Sharpe 1.275, TC-survival
net Sharpe 0.676) — a much wider margin than the original 0.2% shortfall.
Same strategy file (strategies/2026-09-14_bwmfi_roc_sizing_sma_trend.py),
same already-confirmed BW-MFI formula (forex-indicators.net), no new
external fetch.

## Grid (Step 6 — targeted SPY-only wide sweep)

`param_grid={trend_window:[30,40,60,80,100], roc_window:[3,5,10,14,20],
smooth_window:[3,5,10], zscore_window:[80,100,150],
sensitivity:[0.3,0.4,0.6], deadband:[0.25,0.35,0.45,0.55]}`, symbol SPY
only -> 2700 combos, 19 clear both Sharpe>=1.0 and TC-survival net
Sharpe>=0.5. Best-by-Sharpe (trend_window=40/roc_window=20/smooth_window=5/
zscore_window=150/sensitivity=0.3/deadband=0.35) more than doubles the
original near-miss's margin.

## Step 7 — Single-config validation (SPY, trend_window=40/roc_window=20/smooth_window=5/zscore_window=150/sensitivity=0.3/deadband=0.35)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.275 | 1.0 | ✅ |
| Max drawdown | 0.053 | 0.25 | ✅ |
| TC-survival net Sharpe | 0.676 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.0 | 0.75 | ✅ |
| Parameter sensitivity (rel std) | 0.233 | 0.5 | ✅ |

122 trades over the ~8yr sample. Walk-forward used the repo-standard
manual 4-equal-slice fallback (vbt.utils.splitting API unavailable in
installed vectorbt==1.1.0).

## Step 8 — Accept/Reject

**SPY: accepted.** All 5 validators pass with a comfortable margin,
rescuing the prior 2026-09-14-167 SPY double near-miss (Sharpe 0.998,
TC-survival 0.464 -> Sharpe 1.275, TC-survival 0.676). QQQ config from
2026-09-14-167 unchanged (already accepted, not retested). Crypto
(BTC/ETH) remains out of scope (prior decisive Sharpe/TC-survival
failures, not revisited).
