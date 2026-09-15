# Backtest Report: Overnight Gap Fade (Intraday Mean Reversion)

**Date:** 2026-09-16 (iteration 2, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-16_gap_fade_intraday.py`

## Hypothesis

Per a Google AI-overview summary of gap-fade mean-reversion writeups
(JournalPlus/Tickerly/StockAlarm), stocks/ETFs that open with a significant
gap vs. the prior close tend to partially reverse intraday absent a genuine
catalyst. Source's own rules are intraday (15-min opening-range wait, sub-
daily execution) and unimplementable with this repo's daily-bar-only
equity loader; adapted here to the daily-bar interface: take a fade
position AT THE OPEN, held to THAT SAME DAY's CLOSE (flat overnight),
whenever `abs(gap) = abs(open - prior_close)/prior_close` exceeds
`gap_threshold` but stays below `max_gap_threshold` (excludes probable
fundamental/news gaps, approximated by size cutoff since no catalyst feed
exists). First "gap fade"/intraday-mean-reversion-of-the-open entry in this
repo (0 prior matches for "gap fade" in `strategies_index.jsonl`) — distinct
from every prior overnight-gap strategy in this repo, which all trade the
close-to-open overnight return itself rather than the open-to-close fade.

Source read via `browser_exec` fallback (Google AI overview) after
`web_search`'s DDGS backend again failed with the same Yahoo/TLS
RequestError as iteration 1 this trigger.

## Grid test summary (Step 6)

`param_grid={gap_threshold: [0.005,0.01,0.02], max_gap_threshold:
[0.05,0.08]}`, `symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`.

- total_cells: 72, passed_cells: 8, **pass_fraction: 0.111**
- by_asset_class: equity 8/36 passed, crypto 0/36 passed (crypto: 24/7
  markets have no meaningful "prior session close vs. open" gap under a
  daily-bar boundary at UTC midnight — near-zero trade counts, degenerate
  metrics)
- by_vol_regime: low 4/24, mid 4/24, high 0/24 — edge (where present) is
  confined to calmer regimes and inverts in high-vol (large gaps trend/
  continue rather than fade during stress, consistent with the source's
  own "avoid fading large fundamental gaps" caveat, which this repo has no
  way to implement precisely)
- best_cell: equity/QQQ/low-vol, sharpe 1.70 (gap_threshold=0.005,
  max_gap_threshold=0.05)
- worst_cell: equity/QQQ/high-vol, sharpe -1.23 (gap_threshold=0.01,
  max_gap_threshold=0.08)

## Single-config validator results (Step 7)

Config selected: `gap_threshold=0.01, max_gap_threshold=0.05` (best pass
count/avg-Sharpe combination from the grid for this config family).

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Overall |
|---|---|---|---|---|---|---|
| QQQ | -0.273 (fail) | 0.292 (fail) | -0.507 (fail) | 0.25 (fail) | 0.862 rel-std (fail) | REJECT |
| SPY | -0.204 (fail) | 0.257 (fail) | -0.481 (fail) | 0.50 (fail) | 1.845 rel-std (fail) | REJECT |
| BTC/USDT | degenerate (0 trades, gap almost never fires under daily/UTC boundary) | — | — | — | fail (NaN) | REJECT (infeasible construction for 24/7 markets) |

## Decision

**Reject across all symbols.** The grid's apparent low/mid-vol-tercile edge
does not survive full-sample validation on either QQQ or SPY — walk-forward
fails decisively (only 1 of 4 splits positive on QQQ, 2 of 4 on SPY),
parameter sensitivity is very high (near/over 1.0 relative std, meaning
Sharpe flips sign across the grid), and net-of-cost Sharpe is negative on
both equity symbols (high trade count from the tight gap_threshold erodes
any edge). Crypto is a structurally poor fit for this construction (daily
UTC-midnight boundaries don't correspond to a real "session gap" in a
24/7 market). Strategy file and this report kept as the record of a
rejected attempt — do not re-test this exact daily-bar gap-fade
construction without a materially different gap-sizing/regime-filter
approach.
