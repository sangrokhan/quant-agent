# Naked (Untested) Weekly Point-of-Control Magnet Bounce

**Strategy file:** `strategies/2026-09-17_naked_poc_magnet_bounce.py`
**Source:** LuxAlgo "Naked POC" / "Point of Control" concept
(https://www.luxalgo.com/library, discovered via browser_exec Google SERP
snippets this iteration -- the direct concept page 404'd; formula
confirmed from LuxAlgo's own repeated disclosed definition across
multiple of their pages: "A naked POC (also called a virgin POC, or NPOC)
is a prior session's point of control that price has not traded back
through since that session ended.").

## Hypothesis

A naked/untested weekly point-of-control (POC) -- a volume-weighted price
level from a completed week that price has not revisited since -- acts as
a "magnet" that the market tends to eventually retrade through. This
strategy enters long when price pulls back near (within tolerance) a
currently-naked POC below the current close, in the direction of an
established uptrend (close > SMA(100)), targeting either a fixed
profit-target above the POC or exiting once the POC gets filled. First
DISCRETE weekly-period POC-tracking construction in this repo, distinct
from all 4 prior Volume-Profile strategies here which use a continuously
rolling N-day window recomputed every bar (2026-09-04-150, 2026-09-08-129,
2026-09-10-001, 2026-09-16-183).

## Grid test (validation/grid_test.py::run_strategy_grid)

- Params: magnet_tolerance_pct in {0.005, 0.01, 0.02}, profit_target_pct in {0.02, 0.03}
- Symbols: QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
- vol_regime_splits=3, 2018-01-01 to 2026-09-01
- 72 total cells, only 3 passed -> **pass_fraction = 0.042**
- By asset class: equity 3/36, crypto 0/36 (decisive)
- By vol regime: low 3/24, mid 0/24, high 0/24
- Best cell: SPY, magnet_tolerance_pct=0.02/profit_target_pct=0.03, low-vol tercile, Sharpe 1.66

## Extended local parameter search

A dedicated sweep (magnet_tolerance_pct x profit_target_pct, 20 combos per
symbol) beyond the coarse grid found the best FULL-SAMPLE Sharpe achievable
was still well below the 1.0 threshold for both equities:
- QQQ: best Sharpe 0.626 (tol=0.03, target=0.04)
- SPY: best Sharpe 0.762 (tol=0.015, target=0.03)

## Verdict: REJECTED (all symbols)

The naked-POC magnet effect does show SOME signal concentrated in
low-vol-regime slices (grid cells reaching Sharpe 1.66), but it does not
survive full-sample blending -- the effect is too weak/rare relative to
false signals in mid/high-vol regimes and does not generalize across the
full vol cycle. Crypto is rejected decisively (0/36), likely because the
weekly-POC magnet concept, borrowed from intraday/session-based futures
trading, is a weaker fit for continuously-traded 24/7 crypto markets with
no natural weekly session boundary the way equities have (Mon-Fri trading
weeks vs crypto's uninterrupted calendar).

**Lesson for future loops:** the coarse-bin (n_bins=10) HLC3-based weekly
volume profile used here is a fairly crude approximation of a true
intraday-tick volume profile; a future revisit could try a finer bin
count or a different period boundary (e.g. monthly instead of weekly) but
given the magnitude of the gap to threshold (0.63-0.76 vs needing 1.0),
this specific construction is not a promising near-miss worth prioritizing.
