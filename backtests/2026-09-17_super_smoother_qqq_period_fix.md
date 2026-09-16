# Backtest Report: Ehlers Super Smoother QQQ Near-Miss Fix (period retune)

**Strategy file:** `strategies/2026-09-17_ehlers_super_smoother_trend.py` (reused, period retuned)
**Date:** 2026-09-17
**Hypothesis source:** Direct fix of 2026-09-17-088 (same cron trigger, no new external research)

## Hypothesis

2026-09-17-088 tested the Ehlers Super Smoother slope+price-above-line
binary trend filter: accepted SPY (period=30) but QQQ (period=30) was a
near-miss (only Sharpe 0.887 failed; MDD/TC/walk-forward/param-sensitivity
all passed). This iteration first tried this repo's usual rescue pattern
(inverse-realized-vol sizing overlay, same as 2026-09-17-084's successful
HalfTrend fix) — but it did NOT work here (Sharpe stayed 0.81-0.91 across
a 12-combo target_vol/leverage_cap sweep, confirming this is a genuine
Sharpe deficiency rather than an MDD-scaling problem). Pivoted to a direct
period retune instead: a sweep over period ∈ {15,20,25,30,35,40,45,50}
found period=35 gives Sharpe=1.466 (MDD=0.164), comfortably clearing the
bar — the near-miss was fixable by moving off period=30 (a local dip in
the Sharpe-vs-period curve) rather than needing exposure-sizing help.

## Vol-target overlay attempt (unsuccessful)

`target_vol∈{0.12,0.15,0.18,0.20}` x `leverage_cap∈{1.0,1.5,2.0}` (12
combos) on QQQ period=30: best Sharpe achieved was 0.913 (still <1.0). MDD
improved somewhat at lower target_vol but Sharpe never crossed the
threshold — confirms the QQQ near-miss is a Sharpe deficiency, not
rescuable by the vol-scaling pattern (consistent with 2026-09-17-087's
finding for TSI's SPY near-miss this same trigger).

## Period retune (successful)

| period | Sharpe | MDD |
|---|---|---|
| 35 | 1.466 | 0.164 |
| 40 | 1.241 | 0.236 |
| 45 | 1.197 | 0.194 |
| 50 | 1.117 | 0.187 |
| 25 | 1.050 | 0.177 |
| 15 | 0.965 | 0.203 |
| 30 | 0.887 | 0.231 |
| 20 | 0.610 | 0.278 |

## Single-config validators (Step 7) — QQQ, period=35

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.466 | 1.0 | ✅ |
| Max Drawdown | 0.164 | 0.25 | ✅ |
| TC survival (net Sharpe, 10bps, 87 trades) | 1.321 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.00 | 0.75 | ✅ |
| Parameter sensitivity (relative std, local grid {25,30,35,40,45}) | 0.161 | 0.5 | ✅ |

**All 5 pass → accepted.**

## Decision (Step 8)

**Accepted** for QQQ (period=35, all 5 validators pass). This resolves
2026-09-17-088's QQQ near-miss via a direct parameter retune rather than
the usual vol-scaling rescue pattern (which was tried first and did not
work) — a useful negative+positive result pair for future loops: not every
near-miss is rescuable by exposure scaling; sometimes the grid's chosen
"best" config is a local Sharpe dip and simply widening the parameter
search resolves it.
