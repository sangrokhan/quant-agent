# DeMarker(5) Oversold on TLT + Trend Filter (rescue attempt of 2026-09-20-067 near-miss)

**Hypothesis:** Direct follow-up to this cron trigger's own near-miss
(2026-09-20-067, DeMarker(5)<0.10 on TLT with NO trend filter, best Sharpe
0.988). That entry's notes suggested adding a light trend filter as a
possible fix, following this repo's established near-miss-rescue pattern.

## Strategy file
`strategies/2026-09-20_demarker5_tlt_trendfilter_rescue.py`

## Result: rescue attempt makes things WORSE, not better

Full parameter sweep (dem_window in {4,5} x oversold_threshold in
{0.08,0.10,0.15} x trend_window in {50,100,150,200}) on TLT, full sample
2010-2026: best Sharpe found is **0.796** (dem_window=4,
oversold_threshold=0.08, trend_window=150) -- WORSE than the parent's
untrended best of 0.988. Adding the trend filter cuts the trade count
substantially (TLT spends less time above its own long SMA than
QQQ/SPY do, being a lower-beta, mean-reverting-around-a-range asset over
much of its history) without a compensating quality improvement in the
remaining trades.

## Outcome

**Rejected**, and importantly this is a NEGATIVE finding worth recording
precisely: unlike QQQ (where DeMarker's original 2026-09-04-154 entry
WAS improved by a 200d trend filter), TLT's own oversold-bounce mechanism
does NOT benefit from a trend filter -- Treasuries mean-revert around
their own multi-year range in a way that a trend-following gate actively
works against, since some of TLT's best oversold-bounce trades occur
precisely when TLT is chopping below its own long SMA (a rate-hiking
regime) rather than confirming an uptrend already in place. The parent's
untrended construction (2026-09-20-067) remains the better version of
this idea, even though it too falls short of the acceptance bar.
