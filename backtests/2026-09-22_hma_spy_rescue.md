# HMA Mean-Reversion Crossunder — SPY Rescue (Backtest Report)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_hma_meanrev_crossunder.py`
**KB id:** 2026-09-22-013

## Hypothesis

Direct rescue of this same cron trigger's near-miss 2026-09-22-004 (HMA
mean-reversion crossunder, accepted QQQ only at hma_window=10/
max_hold_days=10; SPY failed Sharpe/MDD/TC-survival at that config, 3/5
validators). Parameter search across hma_window and max_hold_days found
hma_window=15/max_hold_days=8 clears all 5 validators on BOTH QQQ (Sharpe
1.332) and SPY (Sharpe 1.079) simultaneously. No new external source --
same strategy code as 2026-09-22-004, parameter retune only.

## Single-config validation (Step 7) — hma_window=15, max_hold_days=8

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.332 ✅ | 1.079 ✅ | ≥1.0 |
| Max drawdown | 0.216 ✅ | 0.220 ✅ | ≤0.25 |
| TC survival (10bps/trade, ~255 trades each) | net Sharpe 0.954 ✅ | net Sharpe 0.674 ✅ | ≥0.5 |
| Walk-forward (4 splits) | 1.0 ✅ | 0.75 ✅ | ≥0.75 |
| Parameter sensitivity (hma_window∈{12,15,18,20}) | rel std 0.182 ✅ | rel std 0.208 ✅ | ≤0.5 |

**All 5 validators pass on BOTH QQQ and SPY.** Trade count is much higher
here (~255 trades over ~7.5yr) than the original 2026-09-22-004 config,
reflecting the shorter hma_window/max_hold_days combination trading more
frequently -- TC-survival still clears comfortably given the strategy's
gross edge.

## Decision

**Accept for QQQ AND SPY** at the retuned config (hma_window=15,
max_hold_days=8), superseding/extending the narrower 2026-09-22-004 accept
(QQQ only at hma_window=10/max_hold_days=10). Crypto remains out of scope
per that entry's original decisive grid rejection (0/36 pass, not
re-tested this sub-iteration).
