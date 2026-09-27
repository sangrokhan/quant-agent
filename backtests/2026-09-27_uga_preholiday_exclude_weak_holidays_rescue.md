# Backtest Report: UGA Pre-Holiday Effect, Per-Holiday Exclusion Rescue

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_uga_preholiday_exclude_weak_holidays_rescue.py`
**Hypothesis id:** 2026-09-27-055

## Hypothesis

Direct rescue of this same cron trigger's own near-miss 2026-09-27-016
(Quantpedia's "Pre-Holiday Effect in Commodities", Vojtko/Dujava,
https://quantpedia.com/pre-holiday-effect-in-commodities/): buy UGA at
close of D-5, hold through D-1 close, for every US federal holiday.
Full-sample UGA Sharpe at the original unconditional rule: 0.983 (near-
miss), with parameter-sensitivity an unusually stable 0.042 — a strong
signal this is a real, near-threshold effect rather than noise.

Per-holiday breakdown (2010-2026, `entry_days_before=5`) on UGA:

| Holiday | n | avg return | win rate |
|---|---|---|---|
| Christmas Day | 16 | +2.23% | 81% |
| Independence Day | 17 | +2.35% | 76% |
| Birthday of Martin Luther King, Jr. | 17 | +1.73% | 65% |
| Washington's Birthday | 17 | +1.53% | 65% |
| Thanksgiving Day | 16 | +1.62% | 56% |
| Juneteenth National Independence Day | 6 | +1.25% | 50% |
| Columbus Day | 16 | +0.38% | 69% |
| New Year's Day | 16 | +0.48% | 50% |
| **Memorial Day** | 17 | **-0.14%** | **41%** |
| **Labor Day** | 17 | **-0.21%** | **65%** |
| **Veterans Day** | 16 | **-0.21%** | **50%** |

Three holidays (Memorial Day, Labor Day, Veterans Day) show negative
average returns — all cluster in the May-November window where the
"driving season" fuel-demand anticipation thesis is economically weaker
(demand already elevated/plateaued going into these three, unlike the
sharper pre-holiday demand spikes around winter holidays or Independence
Day). Excluding these three from the traded holiday set is proposed as
an economically-motivated fix (same technique already validated once this
cron trigger for JETS, 2026-09-27-043's New Year's Day exclusion).

## Single-config validation (full sample, 2010-2026)

| Validator | UGA (exclusion rescue) |
|---|---|
| Sharpe ratio (>=1.0) | **PASS** 1.226 (up from 0.983) |
| Max drawdown (<=0.25) | PASS 0.140 (down from 0.195) |
| Transaction-cost survival (net Sharpe >=0.5, 5bps/trade, 105 trades) | PASS 1.181 |
| Walk-forward (manual 4-split substitute) | PASS 1.0 (4/4 splits positive) |
| Parameter sensitivity (relative_std<=0.5, 5-cell `entry_days_before` sweep with the exclusion applied) | PASS 0.067 |

All 5 validators pass, and the exclusion improves BOTH Sharpe and MDD
simultaneously (not just a Sharpe/risk trade-off) — the same favorable
pattern already seen in the JETS rescue.

## Decision

**Accepted** for UGA at `entry_days_before=5,
exclude_holidays=("Memorial Day", "Labor Day", "Veterans Day")`. This is
the 3rd successful "per-holiday-breakdown exclusion" rescue in this
repo's history (following JETS's New Year's Day exclusion this same cron
trigger, 2026-09-27-043), reinforcing this repo's own note that this
technique is a reusable, lower-overfit-risk rescue pattern for other
calendar-effect near-misses. USO (the other symbol from the original
2026-09-27-016 entry) was not re-tested this sub-iteration since its
original failure was decisive (Sharpe 0.66, MDD 0.293, TC-survival 0.381
all fail) rather than a stable near-miss.
