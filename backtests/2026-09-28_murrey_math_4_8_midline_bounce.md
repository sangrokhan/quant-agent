# Murrey Math 4/8 Midline Support-Bounce — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_murrey_math_4_8_midline_bounce.py`
**Hypothesis source:** https://www.onetradingmarkets.com/otmacademy/academy/murrey-math-lines-support-resistance-guide
(read via `browser_exec`; `web_extract`'s ddgs backend is search-only)

## Hypothesis

Rescue attempt for prior near-miss `2026-09-16-180` (Murrey Math 0/8
"ultimate support" bounce, best cell Sharpe 0.992, pass_fraction 0/216). The
source explicitly ranks the 4/8 line as "the strongest support/resistance
inside the Murrey frame" and "one of the best price areas to look for fresh
long or short setups," versus 0/8 being the rarest/hardest-to-reach
"ultimate" level. Swapped the entry trigger from 0/8-touch-reclaim to
4/8-touch-reclaim, everything else (rolling octave construction from
lookback_n, ATR-free overshoot-buffer stop, time-stop) held structurally
identical to isolate this one variable.

## Grid test (Step 6)

`param_grid={"lookback_n": [32, 48], "overshoot_buffer_mult": [0.25, 0.5]}`,
`symbols={"equity": ["QQQ"]}` (light workload, single asset class per
`suggested_workload=light`), `vol_regime_splits=3`.

- **total_cells:** 12, **passed_cells:** 0, **pass_fraction:** 0.0
- **by_vol_regime:** low 0/4, mid 0/4, high 0/4 — uniformly poor, not
  regime-specific.
- **best_cell:** lookback_n=48, overshoot_buffer_mult=0.25, QQQ, mid-vol,
  Sharpe **0.467** (well under 1.0 threshold, and materially worse than the
  0/8 near-miss's best cell of 0.992).
- **worst_cell:** lookback_n=32, overshoot_buffer_mult=0.25, QQQ, high-vol,
  Sharpe **-1.06**.

## Verdict

**Rejected at grid stage** — decisively worse than the source-alternative
(0/8) already tested and itself rejected. Single-config validators (Step 7)
skipped since the grid result is unambiguous (0/12, best cell Sharpe less
than half the threshold). Finding: the source's own claim that 4/8 is a
"better" level for entries does not transfer to this repo's rolling-window
octave-touch-and-reclaim mechanical construction — likely because 4/8 is
touched far more often than 0/8 (as the source itself notes, price spends
~40% of its time between 3/8 and 5/8), producing many low-quality/noisy
entries rather than the rarer, higher-conviction 0/8 extreme-support
bounces. This closes out the Murrey Math family for this construction style
(both octave choices now tested and rejected).
