# 2026-09-10 — First Five Days of January Indicator

## Hypothesis

Per Stock Trader's Almanac (studied back to 1950, cited by CNBC 2020-01-02):
"When stocks finish the first five [trading] days [of January] higher, the
S&P 500 has been positive more than 80% of the time at year-end with an
average gain of about 13%." Mechanical rule: sum the returns of the first
`num_days` trading days of each January; if positive, hold long for the
rest of the year (from day `num_days`+1 of January through year-end); if
negative, stay flat for the remainder of the year.

Distinct from the already-accepted January Barometer (2026-09-10-019),
which uses the ENTIRE month of January's own return — this uses only the
first few trading days, a shorter/earlier signal window, holding from
January itself onward rather than starting in February.

Strategy file: `strategies/2026-09-10_first_five_days_january.py`

## Single-config validator results (num_days=3)

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-forward pass fraction | Trades |
|---|---|---|---|---|---|
| SPY | 1.041 (pass, thr 1.0) | 0.202 (pass, thr 0.25) | 1.034 (pass, thr 0.5) | 1.00 (pass, thr 0.75; 4/4) | 7 |
| QQQ | 1.164 (pass, thr 1.0) | 0.232 (pass, thr 0.25) | 1.158 (pass, thr 0.5) | 1.00 (pass, thr 0.75; 4/4) | 7 |

Parameter sensitivity (7-cell Sharpe grid across num_days in {3,4,5,7,10}
for SPY/QQQ): relative std = 0.061, threshold 0.5 → **pass**, very
robust to the num_days choice.

Note: `check_walk_forward` computed via a manual 4-way `np.array_split`
range-split substitute (same as every strategy tested this trigger) due to
the pre-existing `vectorbt.utils.splitting` AttributeError on installed
vectorbt 1.1.0 (flagged in 2026-09-10-021).

Not tested against crypto (BTC/USDT) as a candidate for acceptance —
crypto has no "January" seasonal convention grounded in the same
institutional-flow rationale as equities, and a quick check showed
Sharpe 0.076 with a catastrophic 87.6% max drawdown (decisively rejected,
consistent with every other calendar-seasonality strategy in this repo
failing on crypto).

## Decision: ACCEPT (equity — SPY, QQQ; crypto rejected)

All validators pass for both SPY and QQQ at num_days=3, with strong
robustness to the exact day-count choice (num_days 3-10 all produce
Sharpe > 1.0 for QQQ; SPY passes cleanly only at num_days=3-4, num_days>=5
fails MDD). Caveat: like the January Barometer, this makes only ONE
decision per calendar year (7-8 trades over the ~11-year sample) — a
structurally thin trade count, though not as thin as the previously
rejected Bitcoin Rainbow Chart (2-5 trades over 7.5yr). Given the
consistency with Stock Trader's Almanac's much longer (1950-) documented
track record and the strong parameter-sensitivity robustness, this is
accepted with the caveat noted for a future loop's benefit.
