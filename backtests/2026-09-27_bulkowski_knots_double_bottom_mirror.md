# Bulkowski "Knots" Double-Bottom Mirror — rejected

**Hypothesis:** bullish long-only mirror of Bulkowski's "Trading Knots"
(https://thepatternsite.com/TradingKnots.html, 2020-09-28): after a Double
Bottom breaks out upward, if a >=3-bar low-range "knot" congestion sits
near/at the pattern's own confirmation price within the preceding
downtrend, the subsequent rally should meet/exceed the pattern's own
measured-move target with elevated odds (mirroring source's own 70%
double-top-decline statistic). First "Knots" strategy in this repo.

**Strategy file:**
`strategies/2026-09-27_bulkowski_knots_double_bottom_mirror.py`

## Grid test (Step 6)

`param_grid={bottom_tolerance_pct:[0.015,0.02,0.03],
knot_price_tolerance_pct:[0.02,0.03,0.05]}`, symbols equity=[QQQ,SPY]
crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2018-2026.

- pass_fraction 0.176 (19/108); by_asset_class equity 14/54, crypto 5/54;
  by_vol_regime low 13/36, mid 6/36, high 0/36 (no high-vol edge at all).
- Best cell Sharpe 2.29 (SPY, bottom_tolerance_pct=0.03,
  knot_price_tolerance_pct=0.02, low-vol tercile only).

## Full-sample check

At the grid's best config (bottom_tolerance_pct=0.03,
knot_price_tolerance_pct=0.02): QQQ full-sample Sharpe 0.034 (18 trades,
MDD 37.4%), SPY full-sample Sharpe 0.781 (23 trades, MDD 15.0%). A 15-combo
local search over `bottom_tolerance_pct in [0.015..0.05] x
knot_price_tolerance_pct in [0.02,0.03,0.05]` on each symbol independently
found ceilings of **0.762 (QQQ)** and **0.820 (SPY)** — neither clears the
1.0 Sharpe threshold, and the two symbols' best configs don't coincide (QQQ
peaks at the loosest tolerances 0.05/0.05, SPY at the tightest 0.04/0.02),
so no single shared config works either.

## Outcome

**Rejected** — full-sample Sharpe ceiling ~0.76-0.82 on both QQQ and SPY
across a reasonably wide local parameter search, decisively below the 1.0
threshold; grid-level "pass" cells are concentrated in the low-vol tercile
only (0/36 in high-vol) and don't reflect a viable full-sample edge. The
knot-congestion filter, while mechanically implementable, does not appear
to add enough discriminating power over a plain double-bottom breakout at
daily-bar granularity to clear this repo's Sharpe bar.
