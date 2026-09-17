# Backtest Report: One Percent A Week Part 2 (Adaptive Weekly System)

**Strategy file:** `strategies/2026-09-18_one_percent_week_part2_tqqq.py`
**Hypothesis id:** 2026-09-18-003
**Source:** https://traders.com/Documentation/FEEDbk_docs/2026/06/TradersTips.html (TASC Jun 2026, Dion Kurczek, "One Percent A Week... Part 2: Variations And Community Enhancements", fully disclosed EasyLanguage)

## Hypothesis

Enter long at the first trading day of a new calendar week; apply five adaptive
exit rules through the week: (1) momentum-failure exit if day 1 was strong
(ProfitPct > 2.0%) but day 2 weakens (ProfitPct < 3.0%); (2) hard stop at
EntryPrice*HardLossMult once ProfitPct <= LossArmPct; (3) an EXPANDING profit
target (base *1.07, widened *1.011 once ProfitPct>0.3%); (4) a "recovery" exit
on any day the bar closes below its own open while in the trade; (5) hard
Friday close-out. Distinct from the two already-tested "One Percent A Week"
variants in this repo (2026-09-12-145 Part-1 adaptive with Tuesday-only fade
exit; 2026-09-13-001 plain base version) -- this Part 2 adds momentum-failure
day-2 check + expanding target + close-below-open recovery exit, none present
in the prior variants.

## Grid Test Summary (Step 6)

Grid: `target_mult` in {1.05,1.07,1.10}, `loss_arm_pct` in {-1.0,-1.3,-2.0},
symbols equity {TQQQ, QQQ} + crypto {BTC/USDT} (day-of-week weekly logic
still computable on crypto's daily bars, though the strategy's own economic
rationale is equity-specific), vol_regime_splits=3.

- total_cells: 81, passed_cells: 36, **pass_fraction: 0.444**
- by_asset_class: equity 36/54, crypto 0/27 (edge entirely equity, as expected
  for a weekly calendar-effect-adjacent strategy)
- by_vol_regime: low 18/27, mid 18/27, high 0/27 (edge concentrated low/mid-vol)
- best_cell: QQQ low-vol, target_mult=1.05/loss_arm_pct=-1.3, Sharpe 2.44
- worst_cell: BTC/USDT low-vol, target_mult=1.10/loss_arm_pct=-2.0, Sharpe 0.22

## Single-Config Validation (Step 7)

Default TASC config (target_mult=1.07, loss_arm_pct=-1.3) full-sample:
- TQQQ: Sharpe 1.59 (pass), MDD 0.398 (FAIL, >0.25), TC 1.36 (pass) -- TQQQ's
  3x leverage makes the underlying MDD too severe under this exit scheme.
- QQQ: Sharpe 1.10 (pass), MDD 0.286 (FAIL, >0.25), TC 0.56 (pass).

A tighter re-sweep (target_mult, loss_arm_pct, hard_loss_mult) found a
QQQ-passing config at `target_mult=1.03, loss_arm_pct=-0.5, hard_loss_mult=0.995`
(tighter profit target + tighter stop cuts drawdown without killing Sharpe):

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward (4-slice) | Param sensitivity (rel std, sweep target_mult) | Verdict |
|--------|--------|-----|------------------------|------------------------|--------------------------------------------------|---------|
| QQQ    | 1.380  | 0.192 | 0.724                 | 1.0 (4/4 pos)           | 0.111                                            | **ACCEPT** |

TQQQ could not be rescued across a similar re-sweep (best config still ~0.30+
MDD) -- its 3x leverage structurally amplifies drawdown beyond this repo's
0.25 threshold under this exit scheme; rejected. Note this is somewhat ironic
given the source article is specifically about TQQQ, but this repo's stricter
MDD threshold (0.25) doesn't tolerate the leveraged-ETF drawdown profile even
with a well-tuned exit scheme.

## Decision (Step 8)

**Accepted for QQQ only** (the un-leveraged underlying), all 5 validators pass.
TQQQ (the source's actual intended vehicle) and crypto rejected -- the
strategy's edge transfers to the underlying index but not the 3x leveraged
product under this repo's drawdown threshold.
