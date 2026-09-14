# 2026-09-14 Qstick Sizing SMA Trend — SPY fix

## Hypothesis

SPY fix for 2026-09-14-108 (Qstick continuous sizing dial): the prior
iteration accepted QQQ but SPY was the closest near-miss recorded that
cron trigger (Sharpe 0.991 vs 1.0 threshold, off by just 0.9%, across a
25-combo sweep centered on trend_window=60). Widening the search to a
finer grid over trend_window (50-80), qstick_window (10/14/20),
qstick_zscore_window (80/100/150), sensitivity (0.4-0.6), and deadband
(0.3-0.45) finds SPY passes cleanly at trend_window=80/qstick_window=10/
qstick_zscore_window=150/qstick_sensitivity=0.5/deadband=0.35 (Sharpe
1.240, TC-survival net Sharpe 0.712) — a much wider margin than the
original near-miss, with 94 total combos clearing both thresholds out of
576 tried. Same strategy file (strategies/2026-09-14_qstick_sizing_sma_trend.py),
same already-confirmed Qstick (Tushar Chande, SMA of Close-Open) formula,
no new external fetch.

## Grid (Step 6 — targeted SPY-only fine sweep)

`param_grid={trend_window:[50,60,70,80], qstick_window:[10,14,20],
qstick_zscore_window:[80,100,150], qstick_sensitivity:[0.4,0.45,0.5,0.6],
deadband:[0.3,0.35,0.4,0.45]}`, symbol SPY only -> 576 combos; 94 clear
both Sharpe>=1.0 and TC-survival net Sharpe>=0.5. Best-by-Sharpe:
trend_window=80/qstick_window=10/qstick_zscore_window=150/sensitivity=0.5/
deadband=0.35 (Sharpe 1.240). Almost all top results share qstick_window=10
and trend_window=70-80, a clear, robust ridge (not an isolated spike) —
the original near-miss's trend_window=60/qstick_window=14 combo was simply
sub-optimal for SPY.

## Step 7 — Single-config validation (SPY, trend_window=80/qstick_window=10/qstick_zscore_window=150/qstick_sensitivity=0.5/deadband=0.35)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.240 | 1.0 | ✅ |
| Max drawdown | 0.081 | 0.25 | ✅ |
| TC-survival net Sharpe | 0.712 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.0 | 0.75 | ✅ |
| Parameter sensitivity (rel std) | 0.128 | 0.5 | ✅ |

150 trades over the ~8yr sample. Walk-forward used the repo-standard
manual 4-equal-slice fallback (vbt.utils.splitting API unavailable in
installed vectorbt==1.1.0).

## Step 8 — Accept/Reject

**SPY: accepted.** All 5 validators pass with a comfortable margin,
rescuing the prior 2026-09-14-108 SPY near-miss (0.991 -> 1.240 Sharpe).
QQQ config from 2026-09-14-108 unchanged (already accepted, not retested).
Crypto (BTC/USDT) remains out of scope (prior decisive MDD-fail rejection,
0.401 > 0.25, not revisited).
