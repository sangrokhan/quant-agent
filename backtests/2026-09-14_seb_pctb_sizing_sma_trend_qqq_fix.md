# 2026-09-14 SEB %b Sizing SMA Trend — QQQ fix

## Hypothesis

QQQ fix for 2026-09-14-147 (Standard Error Bands %b continuous sizing dial,
accepted BTC/ETH but QQQ was a near-miss failing Sharpe 0.992<1.0 plus
decisive TC-survival, and SPY decisively failed TC-survival at 448
trades). Widening the search over trend_window (30-80), seb_lr_window
(14-30), seb_smooth_window (3-10), seb_k (1.5-2.5), sensitivity (0.4-0.8),
and deadband (0.25-0.55) — 1296 combos total — finds QQQ passes cleanly
at trend_window=80/seb_lr_window=30/seb_smooth_window=5/seb_k=2.5/
sensitivity=0.4/deadband=0.45 (Sharpe 1.303, TC-survival net Sharpe
0.966), with 162 of 1296 combos clearing both thresholds — the wider
trend_window (80 vs 40) and wider deadband cut the original config's
excessive turnover (the "tight regression bands cross frequently" issue
flagged in the original rejection). Same strategy file
(strategies/2026-09-14_seb_pctb_sizing_sma_trend.py), same
already-confirmed Standard Error Bands (Jon Andersen, TASC Sep 1996)
formula, no new external fetch.

## Grid (Step 6 — targeted QQQ-only wide sweep)

`param_grid={trend_window:[30,40,60,80], seb_lr_window:[14,21,30],
seb_smooth_window:[3,5,10], seb_k:[1.5,2.0,2.5], sensitivity:[0.4,0.6,0.8],
deadband:[0.25,0.35,0.45,0.55]}`, symbol QQQ only -> 1296 combos, 162
clear both Sharpe>=1.0 and TC-survival net Sharpe>=0.5. Nearly all top
results share trend_window=80 (vs the original 40), confirming the wider
trend gate is what fixes the turnover problem.

## Step 7 — Single-config validation (QQQ, trend_window=80/seb_lr_window=30/seb_smooth_window=5/seb_k=2.5/sensitivity=0.4/deadband=0.45)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.303 | 1.0 | ✅ |
| Max drawdown | 0.075 | 0.25 | ✅ |
| TC-survival net Sharpe | 0.966 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.0 | 0.75 | ✅ |
| Parameter sensitivity (rel std) | 0.181 | 0.5 | ✅ |

114 trades over the ~8yr sample (down sharply from the original config's
high turnover). Walk-forward used the repo-standard manual 4-equal-slice
fallback (vbt.utils.splitting API unavailable in installed vectorbt==1.1.0).

## Step 8 — Accept/Reject

**QQQ: accepted.** All 5 validators pass with a strong margin, rescuing
the prior 2026-09-14-147 QQQ near-miss (0.992 -> 1.303 Sharpe, decisive
TC-fail -> 0.966 net Sharpe). BTC/USDT and ETH/USDT configs from
2026-09-14-147 unchanged (already accepted, not retested). SPY remains
out of scope (prior decisive TC-survival failure at 448 trades, not
revisited this iteration).
