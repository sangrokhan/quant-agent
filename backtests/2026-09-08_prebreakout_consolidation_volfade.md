# Pre-Breakout Consolidation (Volume Fade) — Backtest Report (REJECTED)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_prebreakout_consolidation_volfade.py`
**Knowledge base id:** 2026-09-08-137

## Hypothesis

Per https://www.investorstack.in/help/tech-pre-breakout-consolidation's
disclosed scanner rule: a stock consolidating within a few percent of its
N-day high, where that high hasn't been broken for the last M days AND
volume is fading during the consolidation, sets up a breakout when price
finally clears the held ceiling. Distinct from Darvas Box (2026-09-05-054,
no volume condition) and Rectangle (2026-09-08-111, midpoint stop, no
volume condition) via its volume-fade-during-consolidation requirement.

## Parameter sweep (before/instead of full grid test)

Systematic sweep of `near_high_pct` in {0.03,0.05,0.08} × `vol_fade_ratio`
in {0.8,0.9,1.0,1.1,1.2} × `lookback_window` in {50,100,150} ×
`max_hold_days` in {10,20,30} (135 combos per symbol) on both QQQ and SPY,
requiring >=15 trades for a result to count:

- Best result across the ENTIRE sweep: **SPY, Sharpe 0.948** (near_high_pct
  in {0.03,0.05,0.08} all tied at vol_fade_ratio=0.8/lookback_window=50,
  26 trades) — still below the 1.0 threshold.
- **QQQ never exceeded Sharpe 0.9** anywhere in the 135-combo sweep.

(Note: a bug was found and fixed during implementation — the initial
rolling-high calculation included the current bar's own close, making a
breakout mathematically impossible; the fixed version excludes today's bar
from the ceiling calculation, and the above sweep uses the fixed version.)

## Decision: REJECTED

No parameter combination across a 135-combo systematic sweep on either
symbol clears the Sharpe 1.0 threshold; SPY's best result (0.948) is a
narrow miss but QQQ never gets close. Given the sweep's comprehensive
coverage and consistently sub-1.0 results, this is a clean reject; the
full grid-test/validator pipeline was skipped per Step 7's minimum-subset
guidance.
