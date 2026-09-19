# Down-Day Streak Band Reversal (rescue attempt of 2026-09-20-065 near-miss)

**Hypothesis:** Direct follow-up to this cron trigger's own recorded
near-miss (2026-09-20-065, N-Day Pullback Reversal): SPY passed 4/5
validators at pullback_days=3/hold_days=5 but failed parameter sensitivity
because a hard N-day cutoff created a cliff at pullback_days=4. This
attempt replaces the hard cutoff with a BAND (`min_streak` to `max_streak`)
of qualifying down-day-streak lengths, hoping the smoother trigger reduces
the cliff sensitivity.

## Strategy file
`strategies/2026-09-20_downstreak_band_reversal_rescue.py`

## Result: rescue attempt FAILS to fix the underlying issue

Widening the band's UPPER bound (`max_streak` from 4 to 6) makes no
difference at all to the full-sample Sharpe (SPY stays at exactly 0.851
for min_streak=2, or exactly 1.006 for min_streak=3, regardless of
max_streak) -- meaning the parameter cliff identified in the parent entry
is driven entirely by the LOWER bound (`min_streak`, i.e. how many
consecutive down days are required to trigger AT ALL), not by any missing
upper cutoff. Sweeping min_streak directly reproduces the exact same
cliff as the parent's `pullback_days` sweep:

| min_streak | hold=3 | hold=5 | hold=7 |
|---|---|---|---|
| 2 | 0.528 | 0.851 | 0.855 |
| 3 | 0.740 | 1.006 | 0.967 |
| 4 | 0.235 | 0.059 | -0.046 |

Parameter sensitivity (min_streak in {2,3,4} x hold_days in {3,5,7}):
rel_std 0.656 vs 0.5 threshold -- **identical failure to the parent**,
because a "band" trigger with an upper bound is mathematically the same
mechanism as the parent's fixed count once the upper bound is wide enough
to never bind (few SPY down-streaks exceed length 4-5 anyway). The fix
attempted here did not address the actual source of fragility.

Grid test (max_streak in {4,5,6} x hold_days in {3,5}, min_streak fixed at
default=2, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2015-2026):
pass_fraction 0.264 (19/72), by_asset_class equity 15/36 crypto 4/36
(slightly better crypto showing than the parent, but still weak), by_vol
regime low 12/24 mid 7/24 high 0/24.

## Outcome

**Rejected** -- same parameter-sensitivity failure as parent
(2026-09-20-065), confirming the fragility is intrinsic to "consecutive
down days as the sole pullback trigger" (regardless of hard-cutoff vs
band framing) rather than an artifact of the exact cutoff mechanic. A
genuinely different fix (e.g. weighting the trigger by MAGNITUDE of the
down days, not just their count, or requiring the streak alongside an
independent confirming condition) would be needed to escape this
fragility -- out of scope for this iteration.
