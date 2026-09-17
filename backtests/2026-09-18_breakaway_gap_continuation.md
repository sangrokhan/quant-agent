# Backtest Report: Breakaway Gap Continuation (rejected, decisive)

**Strategy file:** `strategies/2026-09-18_breakaway_gap_continuation.py`
**Knowledge base id:** 2026-09-18-025

## Hypothesis

Per quantifiedstrategies.com's "Breakaway Gaps: Definition And Trading
Strategy Example With Backtest and Trading Rules" (visited this iteration
via `browser_exec` after `web_extract` errored -- ddgs backend is
search-only): a breakaway gap "opens above yesterday's high and never
trades below yesterday's high," typically on above-average volume,
signaling a new trend start. Tested: gap-up entry (open > prior high, low
stays >= prior high, volume >= vol_mult x its own rolling average), fixed
N-day time-stop exit (source itself tests 1-10 day stops).

## Step 6 grid summary (vol_mult in [1.2,1.5,2.0], time_stop_days in
[3,5,10], symbols=QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3,
2015-2026)

```
total_cells: 108, passed_cells: 0, pass_fraction: 0.0
by_asset_class: equity 0/54, crypto 0/54
by_vol_regime: low 0/36, mid 0/36, high 0/36
best_cell: QQQ low-vol, vol_mult=1.5/time_stop_days=10, Sharpe=0.885 (still fails)
worst_cell: SPY high-vol, vol_mult=1.2/time_stop_days=3, Sharpe=-1.26
```

**Zero cells passed out of 108** -- the single best cell (QQQ low-vol
regime) still only reached Sharpe 0.885, short of the 1.0 threshold. This
decisively confirms the source's own admission in the article itself:
"The results show pretty random results... it's difficult to make money on
breakaway gaps" (source's own GLD backtest reached the same conclusion,
here replicated and extended to QQQ/SPY/BTC/ETH).

## Decision

**Rejected, decisively, no further tuning attempted.** Consistent with the
source's own stated finding rather than a surprising result -- the source
explicitly says the standalone-gap version gives "pretty random results,"
and adding further undisclosed rules 2/3 (their exact numeric thresholds
were not rendered in the visible page text -- placeholder "you find the
trading rules at the bottom of the article" recurred instead of the actual
numbers) is not something this iteration will invent from model recall,
per RESEARCH_LOOP.md's explicit prohibition. A future iteration with a
successful extraction of the article's full disclosed rules 2/3 (e.g. via a
different browser rendering pass, or the cached/print version of the page)
could revisit this with the complete 3-rule combination the source reports
as the best-performing version.
