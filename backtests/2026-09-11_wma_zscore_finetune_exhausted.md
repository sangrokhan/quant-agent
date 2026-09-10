# Backtest report: WMA standalone trend filter + Price Z-Score trend
# continuation -- fine-tune attempts on 2026-09-11-038/039 near-misses

**Strategy files:** `strategies/2026-09-11_standalone_wma_trend_filter.py`,
`strategies/2026-09-11_price_zscore_trend_continuation.py` (existing files
from 2026-09-11-038/039, re-parameterized this iteration -- no code
changes)

## Hypothesis

Both are SetupAlpha-sourced "regime filter ranking" strategies originally
accepted QQQ-only with SPY near-misses:
- 2026-09-11-038 (WMA standalone): `close > WMA(close, wma_window)`, SPY
  near-miss best 0.906 at the original grid.
- 2026-09-11-039 (Price Z-Score): `(close - mean)/std > z_threshold`, SPY
  near-miss best 0.90 at the original grid.

This iteration attempts a fine local parameter search on SPY for both,
following the fix pattern that succeeded for BDRY/GDX-GLD/XLF-SPY/CTM
earlier this cron trigger.

## Parameter search (Step 6/7)

**WMA standalone**: fine sweep wma_window in range(30,260,10), then a
refined sweep around the best region (180-200, step 2). Best SPY Sharpe
found: **0.988** at wma_window=188 (MDD 0.189, which alone would pass) --
still below the 1.0 Sharpe threshold. No configuration in the full sweep
(30-250 step 10, then 180-200 step 2) cleared 1.0.

**Price Z-Score**: sweep z_window in {50,75,100,125,150,175,200,225,250} x
z_threshold in {-0.5,-0.25,0.0,0.25,0.5,0.75,1.0} (63 combos). Best SPY
Sharpe found: **0.980** at z_window=75/z_threshold=-0.5 (MDD 0.273, which
itself narrowly fails the 0.25 budget). No combo cleared both Sharpe>=1.0
AND MDD<=0.25 simultaneously.

## Decision: REJECTED (fine-tune exhausted for both, near-miss status confirmed rather than improved)

Both strategies remain in their original state: accepted QQQ-only, SPY
near-miss (now confirmed as a "hard" near-miss -- an extensive local search
could not clear the bar, unlike this same cron trigger's successful
fine-tunes of BDRY/GDX-GLD/XLF-SPY/CTM). No code or knowledge-base changes
needed to the original 2026-09-11-038/039 entries; this iteration's finding
is recorded as a new log entry documenting the exhausted search so a future
loop doesn't re-attempt the same local parameter search.

## Notes for future loops

- WMA standalone's best SPY Sharpe (0.988) is extremely close to the 1.0
  threshold -- a future loop might try a slightly different construction
  (e.g. adding a minimal band/hysteresis around the WMA crossing, similar
  to this repo's other "close but need one more twist" fixes) rather than
  pure parameter re-tuning, which appears to have hit its ceiling here.
- Price Z-Score's best-Sharpe config (0.980) trades off against its worst
  MDD (0.273) -- the Sharpe/MDD tradeoff frontier for this strategy doesn't
  have a point where both clear simultaneously in the tested space; a
  different exit/stop-loss mechanism (this repo's other successful fix
  pattern for MDD-only failures, e.g. 2026-09-10-041 yield-curve) might be
  worth trying in a future loop rather than further parameter-only tuning.
