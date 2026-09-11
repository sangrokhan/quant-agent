# 2026-09-11 Short the Close, Cover at the Next Open — Backtest Report

**Hypothesis:** Overnight short: short at today's close, cover at
tomorrow's open, gated by (1) today's open no more than 1.5% above
yesterday's close, and (2) today's daily range (High-Low) exceeding its
own 20-day average. Source: Google AI-overview synthesis of
https://www.quantifiedstrategies.com/short-the-close-cover-at-the-next-open/
(visited this iteration via browser_exec Google-search fallback after
the direct URL returned a 404; the AI-overview snippet fully disclosed
both numeric conditions).

## Single-config validators (default gap_thresh=0.015, range_window=20, SPY/QQQ, 2010-2024)

| Symbol | Sharpe | MDD | Cumulative return |
|---|---|---|---|
| SPY | -0.577 (fail) | 0.598 (fail) | -59.7% |
| QQQ | -0.681 (fail) | 0.727 (fail) | (negative, catastrophic) |

## Decision: REJECTED (decisive, both symbols, no fine-tune attempted)

Both symbols show strongly NEGATIVE Sharpe and catastrophic drawdowns
(60-73%) -- this is an unconditional structural loser given equities'
well-known long-run positive drift: shorting overnight on ~40% of all
trading days (1422/3522 for SPY -- the gap/volatility filters are not
selective enough to avoid the persistent overnight-long-drift effect
this repo has already validated positively in the opposite direction,
see accepted overnight-drift-long strategies). No fine-tune sweep was
run given how decisively negative the raw result is (a negative-Sharpe
result driven by fighting a known persistent drift is not something
parameter tuning within the same mechanism is likely to fix).

## Notes for future iterations

- This confirms (from the short side) what this repo's already-accepted
  long overnight-drift strategies already established: US equity indices
  have a robust positive overnight (close-to-open) drift on average.
  Systematically shorting overnight, even with a gap/volatility filter
  meant to select "high-conviction" setups, loses money decisively.
- The AI-overview-sourced numeric rule (1.5% gap cap, range>20-day-avg)
  could not be verified against the ORIGINAL article's exact wording
  (the direct URL 404'd) -- if a future iteration finds the live article,
  cross-check the disclosed thresholds match this reconstruction before
  assuming this rejection definitively closes the door on the "short
  the close" family; a different, more selective filter (e.g. requiring
  a confirmed reversal candle pattern like Dark Cloud Cover, already
  accepted-adjacent in this repo) might avoid the persistent-drift
  headwind better than a pure gap/volatility gate.
