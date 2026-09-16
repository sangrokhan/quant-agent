# Backtest Report: HalfTrend Vol-Target Sizing Overlay (QQQ Near-Miss Fix)

**Strategy file:** `strategies/2026-09-17_halftrend_voltarget_qqq_fix.py`
**Date:** 2026-09-17
**Hypothesis source:** Direct fix of 2026-09-17-083 (same cron trigger, source already confirmed -- no new external research this sub-iteration)

## Hypothesis

2026-09-17-083 tested the HalfTrend (everget) binary long/flat trend-state
gate: accepted SPY (amplitude=6), but QQQ (amplitude=2) was a genuine
near-miss -- Sharpe 1.42, TC-survival 1.36, walk-forward 1.0,
param-sensitivity 0.14 all pass, only MDD (0.255) marginally exceeded the
0.25 cap. This iteration applies this repo's standard rescue pattern:
scale exposure inversely to rolling realized volatility
(`target_vol / realized_vol`, clipped to `[0, leverage_cap]`) on top of the
same binary HalfTrend gate, damping drawdowns during rare high-vol
whipsaw periods.

## Parameter search

Hand sweep over `target_vol ∈ {0.10,0.12,0.15,0.18}` x
`leverage_cap ∈ {0.8,1.0,1.2}` on QQQ (amplitude=2 fixed, same as
2026-09-17-083's near-miss config): all 12 combos passed both Sharpe>1.0
and MDD<0.25, confirming the vol-target overlay robustly fixes the
near-miss rather than requiring fragile tuning. Best config selected:
target_vol=0.12, leverage_cap=0.8 (Sharpe 1.47, MDD 0.122).

SPY (amplitude=6, same as 2026-09-17-083's accepted config) similarly
improves with the same overlay: target_vol=0.12, leverage_cap=1.0 gives
Sharpe 1.09, MDD 0.112 (down from the binary version's already-passing
0.149).

Crypto (BTC/USDT, ETH/USDT, amplitude=6) was also tested with this overlay
across target_vol∈{0.10,0.15,0.20} x leverage_cap∈{0.3,0.5}: Sharpe stayed
in the 0.19-0.22 range throughout (well below 1.0) -- the vol-target
overlay reduces MDD somewhat but cannot rescue crypto here because the
underlying gross Sharpe itself is too low (not just an MDD-scaling
problem, unlike the QQQ/SPY equity case). Not pursued further.

## Single-config validators (Step 7)

### QQQ (amplitude=2, target_vol=0.12, leverage_cap=0.8)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.472 | 1.0 | ✅ |
| Max Drawdown | 0.122 | 0.25 | ✅ |
| TC survival (net Sharpe, 10bps, 182 trades) | 0.912 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.00 | 0.75 | ✅ |
| Parameter sensitivity (relative std) | 0.016 | 0.5 | ✅ |

**All 5 pass → accepted.**

### SPY (amplitude=6, target_vol=0.12, leverage_cap=1.0)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.094 | 1.0 | ✅ |
| Max Drawdown | 0.112 | 0.25 | ✅ |
| TC survival (net Sharpe, 10bps, 155 trades) | 0.713 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.00 | 0.75 | ✅ |
| Parameter sensitivity (relative std) | 0.032 | 0.5 | ✅ |

**All 5 pass → accepted.**

## Decision (Step 8)

**Accepted** for both QQQ and SPY (both all 5 validators pass, per-symbol
tuned target_vol/leverage_cap). This resolves 2026-09-17-083's QQQ
near-miss and confirms the vol-target rescue pattern's applicability to a
fourth indicator family this cron trigger. Crypto not pursued: the
vol-target overlay cannot fix a Sharpe deficiency, only an MDD-scaling
problem.
