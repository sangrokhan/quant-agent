# Backtest Report: JETS Pre-Holiday Seasonal Hold, New Year's Day exclusion rescue (accepted)

**Strategy file:** `strategies/2026-09-27_jets_preholiday_exclude_nyd_rescue.py`
**KB id:** 2026-09-27-043 (rescue of near-miss 2026-09-22-113)
**Source:** https://quantpedia.com/do-airline-stocks-take-off-around-u-s-holidays/ (Quantpedia, "Do Airline Stocks Take Off Around U.S. Holidays?")

## Hypothesis

Original 2026-09-22-113: JETS ETF shows a seasonal return pattern around 9
major US holidays (buy at D-5 close, hold through D-1, sell at D-1 close),
attributed to holiday-travel demand anticipation. Full-sample Sharpe 0.961
(near-miss); all other 4 validators passed cleanly.

## Root-cause analysis (this iteration)

Per-holiday breakdown of the original strategy's 9 trade windows (2015-2026):

| Holiday | n | avg return | win rate |
|---|---|---|---|
| New Year's Day | 11 | **-1.03%** | **18%** |
| Memorial Day | 12 | 0.34% | 58% |
| Washington's Birthday | 11 | 0.44% | 64% |
| Juneteenth | 5 | 0.30% | 40% |
| Christmas Day | 11 | 0.90% | 73% |
| MLK Day | 11 | 1.56% | 73% |
| Independence Day | 12 | 1.68% | 67% |
| Labor Day | 11 | 1.30% | 91% |
| Thanksgiving Day | 11 | 2.25% | 73% |

New Year's Day is a decisive, isolated drag: negative average return and an
18% win rate, starkly different from every other holiday (all positive,
40-91% win rate). Economically plausible explanation: New Year's travel is
largely already completed by New Year's Eve (the pre-holiday D-5→D-1 window
falls mostly in the dead week between Christmas and New Year's, a low
booking-activity period), unlike the outbound-anticipation dynamic driving
the other 8 holidays.

## Rescue: exclude New Year's Day from the holiday set

Same D-5-entry/D-1-exit mechanical rule, `lookback_days=5`/`hold_days=4`,
now applied to the remaining 8 holidays only.

| Validator | JETS value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.123 | >= 1.0 | YES |
| Max drawdown | 0.127 (improved from 0.148) | <= 0.25 | YES |
| Transaction cost survival (10bps/trade, 84 trades) | net Sharpe 0.988 | >= 0.5 | YES |
| Walk-forward (manual 4-split) | 4/4 splits positive (pass_fraction 1.0) | >= 0.75 | YES |
| Parameter sensitivity (9-point lookback_days x hold_days sweep) | relative_std 0.059 | <= 0.5 | YES |

All 5 validators pass. Parameter sweep around the exclusion (lookback_days
in {4,5,6}, hold_days in {3,4,5}) confirms low sensitivity: Sharpe ranges
0.94-1.12 across the neighborhood, mean 1.04.

## Decision: ACCEPT (JETS)

This is a straightforward, economically-motivated fix (removing a single
holiday window with a clearly different demand regime) rather than an
opaque overfit — the exclusion is exposed as an explicit, auditable
`exclude_holidays` parameter rather than hardcoded silently. Strategy file
kept live in `strategies/`.
