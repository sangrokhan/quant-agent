# Cup-and-Handle Breakout (O'Neil/CANSLIM specification) — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_cup_and_handle_breakout.py`
**Outcome:** REJECTED (decisive, all cells fail)

## Hypothesis

Per tradiecapital.com's detailed spec (sourced from William O'Neil's
CANSLIM methodology): a bullish continuation pattern where a stock in
an existing uptrend corrects 12-33% in a rounded U-shape over 7-65
weeks (the "cup"), rallies back near its prior high, then drifts down
1-4 weeks on contracting volume in the upper half of the cup (the
"handle" — a final shakeout), before breaking out above the handle's
high on a 40%+ volume surge. First cup-and-handle strategy in this repo.

Sources:
- `google_search:Cup and Handle chart pattern trading strategy breakout rules parameters`
- https://www.tradiecapital.com/blog/cup-and-handle-pattern (full mechanical spec: depth 12-33%, cup duration 7-65 weeks, handle 1-4 weeks/upper-half/contracting volume, breakout volume 40-50%+ above average, stop below handle low, measured-move target = cup depth projected above breakout)

## Implementation note

The source's exact volume-contraction (source: some unspecified "contracting")
and breakout-surge (source: 40-50%+) thresholds needed operationalizing
as `handle_vol_contraction_ratio` and `volume_surge_mult`. At the source's
literal 40%+ volume surge (`volume_surge_mult=1.4`) and any reasonable
volume-contraction threshold tested (0.8-2.0x), ZERO valid setups fired
on QQQ/SPY over 2010-2026 (16 years) — the multi-condition specification
(depth + U-shape + recovery + handle-duration + handle-position +
volume-contraction + volume-surge, all simultaneously) is simply too
restrictive for index ETFs (QQQ/SPY don't exhibit O'Neil's individual
growth-stock volume signature as cleanly). Loosened `volume_surge_mult`
to 0.9-1.0 (i.e. requiring current volume merely near or above its own
20-day average, not a full 40% surge) and `handle_vol_contraction_ratio`
to 1.2-1.5 to get a testable number of setups (10-14 trades over 16
years) — still an extremely rare signal.

## Single-config validator results (handle_vol_contraction_ratio=1.2, volume_surge_mult=0.9)

| Symbol | Sharpe | MDD | TC-adj Sharpe |
|---|---|---|---|
| SPY | 0.297 (FAIL, thr 1.0) | 0.053 (PASS, trivial — barely any exposure) | 0.267 (FAIL, thr 0.5) |
| QQQ | 0.488 (FAIL, thr 1.0) | 0.091 (PASS, trivial) | 0.460 (FAIL, thr 0.5) |

Walk-forward and parameter sensitivity not run given the decisive grid
failure below (not worth the extra compute for an already-rejected
signal).

## Step 6 grid summary

- Grid: `param_grid={handle_vol_contraction_ratio:[1.2,1.5], volume_surge_mult:[0.9,1.0]}`,
  `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
  2010-01-01 to 2026-09-01 (16-year window, deliberately longer than
  this repo's usual 2015/2019 start to give the multi-week pattern more
  chances to occur). 48 total cells.
- `pass_fraction`: **0.0 (0/48) — decisive rejection**
- `by_asset_class`: equity 0/24, crypto 0/24
- `by_vol_regime`: low 0/16, mid 0/16, high 0/16
- `best_cell`: handle_vol_contraction_ratio=1.2, volume_surge_mult=0.9,
  SPY, low-vol, Sharpe 0.901 (still below threshold)
- `worst_cell`: handle_vol_contraction_ratio=1.5, volume_surge_mult=0.9,
  BTC/USDT, high-vol, Sharpe -0.249

## Decision

**Rejected, decisively.** Even after loosening the source's own volume
thresholds substantially (0.9-1.0x average instead of the literal
40-50% surge requirement) to get a testable trade count at all, no grid
cell clears the Sharpe/TC bar. The pattern generates far too few signals
(10-14 trades over 16 years on liquid index ETFs) for a statistically
reliable edge, and the MDD passes are trivial (near-zero market
exposure, not genuine risk control — same failure mode noted for
Morning Star, 2026-09-06-161). Crypto is unsuitable (negative Sharpe in
the worst cell, no cup-and-handle rationale for a 24/7 market with no
earnings-driven institutional accumulation cycle).

This is consistent with the broader pattern in this repo: multi-bar
structural chart patterns (Morning Star, Cup and Handle) requiring many
simultaneous conditions on daily-bar index ETFs are systematically too
rare to validate, versus single-indicator crossover/threshold rules
which fire often enough for meaningful statistics. Future loops
considering another classical chart pattern (e.g. Head and Shoulders,
Double Top/Bottom, Ascending Triangle) should expect the same signal-
scarcity problem on this repo's instrument set and either test on
individual growth stocks (closer to O'Neil's original CANSLIM universe)
or accept a much longer lookback/lower selectivity from the outset.
