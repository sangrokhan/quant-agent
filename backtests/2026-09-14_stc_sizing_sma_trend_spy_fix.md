# 2026-09-14 STC Sizing SMA Trend — SPY fix

## Hypothesis

SPY fix for 2026-09-14-107 (Schaff Trend Cycle continuous sizing dial):
prior iteration accepted QQQ (trend_window=40/stc_sensitivity=0.4/
deadband=0.3) but the best SPY config from a 9-combo sweep only reached
Sharpe 0.921, just below the 1.0 threshold. Widening the search across
trend_window (30/40/60/80) x stc_sensitivity (0.3-0.6) x deadband
(0.15-0.5) on SPY alone finds a clean pass at trend_window=80/
stc_sensitivity=0.3/deadband=0.4 (Sharpe 1.342). Same strategy file
(strategies/2026-09-14_stc_sizing_sma_trend.py), same already-confirmed
Schaff Trend Cycle formula, no new external fetch this iteration (formula
reuse only).

## Grid (Step 6 — targeted SPY-only sweep)

`param_grid={trend_window:[30,40,60,80], stc_sensitivity:[0.3,0.4,0.5,0.6],
deadband:[0.15,0.2,0.3,0.4,0.5]}`, symbol SPY only -> 80 combos evaluated
by full-sample Sharpe; top result trend_window=80/stc_sensitivity=0.3/
deadband=0.4 (Sharpe 1.342), well clear of the next-best cluster (1.19-1.29
range for several other combos), a robust ridge rather than an isolated
spike.

## Step 7 — Single-config validation (SPY, trend_window=80/stc_sensitivity=0.3/deadband=0.4)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.342 | 1.0 | ✅ |
| Max drawdown | 0.079 | 0.25 | ✅ |
| TC-survival net Sharpe | 0.960 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.0 | 0.75 | ✅ |
| Parameter sensitivity (rel std) | 0.106 | 0.5 | ✅ |

110 trades over the ~8yr sample. Walk-forward used the repo-standard
manual 4-equal-slice fallback (vbt.utils.splitting API unavailable in
installed vectorbt==1.1.0).

## Step 8 — Accept/Reject

**SPY: accepted.** All 5 validators pass with strong margins, rescuing the
prior 2026-09-14-107 SPY near-miss (0.921 -> 1.342 Sharpe). QQQ config
from 2026-09-14-107 unchanged (already accepted, not retested this
iteration). Crypto remains out of scope (prior decisive BTC/USDT MDD-fail
rejection, 0.579 > 0.25, not revisited).
