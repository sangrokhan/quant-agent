# Descending Broadening Wedge "Buy at 3rd Touch" — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_descending_broadening_wedge_3rd_touch.py`
**Source:** https://thepatternsite.com/dbw.html

## Hypothesis

Bulkowski's Descending Broadening Wedge: a "megaphone tilted down" where
BOTH trendlines (through swing highs and swing lows) slope downward, with
the lower trendline less steep (range widens while drifting down) --
distinct from this repo's already-tested Broadening Top (upper trendline
up, lower trendline down, a true symmetric megaphone). Source's own
"buy at 3rd touch" tactic: buy when price touches the lower trendline for
the third time and begins rising, targeting the projected upper
trendline. Source's own stats: breakout upward 72% of the time, avg rise
39%.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`pattern_lookback in {60,80,100}` x `touch_tolerance in {0.01,0.015,0.02}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.083 (9/108)**
- by_asset_class: equity 7/54, crypto 2/54
- by_vol_regime: low 2/36, mid 3/36, high 4/36
- best_cell: QQQ, pattern_lookback=60, touch_tolerance=0.02, mid-vol, Sharpe 1.65 (isolated)

Follow-up full-sample check across the same grid on QQQ/SPY: Sharpe
values are weak and inconsistent across the grid, ranging from -0.76 to
0.87 (best: pattern_lookback=80, touch_tolerance=0.01, QQQ Sharpe 0.868),
with very sparse trade counts (as few as 0-5 nonzero-return days for some
cells, e.g. SPY at pattern_lookback=100/touch_tolerance=0.01 had ZERO
trades over the full 2019-2026 sample). No config clears the >= 1.0
Sharpe threshold on both symbols simultaneously.

## Decision

**Rejected.** No config in either the Step 6 grid or the full-sample
follow-up sweep produces a Sharpe >= 1.0 on both QQQ and SPY
simultaneously; several cells have essentially no trades at all, and the
touch-detection mechanical proxy appears too fragile/rare to generate a
reliable edge on daily bars. Not worth running the full validator suite.

## Notes for future loops

The Descending Broadening Wedge's requirement that BOTH trendlines slope
downward (as opposed to the standard Broadening Top's up/down
combination) is a genuinely rarer geometric configuration, and this
daily-bar rolling-trendline-fit proxy struggles to find enough valid,
stable instances of it. A future loop revisiting this pattern should
consider intraday bars (where Bulkowski's own source data is likely
drawn from) or a looser trendline-fit tolerance, though the latter risks
false-positive pattern detection. Given this repo's Broadening Top
already covers the more common variant, this specific "both descending"
subtype may not be worth further pursuit without better pivot detection.
