# Backtest Report: Value Area Reclaim + Bullish Engulfing + Volume Expansion Confirmation (2026-09-18)

**Hypothesis id:** 2026-09-18-063
**Strategy file:** `strategies/2026-09-18_value_area_reclaim_engulfing_confirm.py`
**Source:** https://www.luxalgo.com/library/indicator/value-area-reversion-signals/ (visited this iteration)

## Hypothesis

Direct rescue attempt for 2026-09-10-001 (simple Value-Area-Low reclaim,
rejected decisively: Sharpe 0.016, 102 trades, TC-survival failed). Per
LuxAlgo's Value Area Reversion Signals page, a valid bullish reclaim
requires a bullish ENGULFING candle re-entering the Value Area WITH
EXPANDING VOLUME -- source states these are explicit fakeout filters. This
iteration added both source-mandated filters on top of the existing VAL
reclaim logic.

## Step 6 grid summary (vol_expansion_mult in [1.1,1.3] x profile_window in [15,20], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 48, passed_cells: 0, **pass_fraction: 0.0**
- by_asset_class: equity 0/24 (0%), crypto 0/24 (0%)
- by_vol_regime: low 0/16, mid 0/16, high 0/16 (all zero)
- best_cell: BTC/USDT, high-vol tercile, Sharpe=0.916 (still fails threshold)
- worst_cell: ETH/USDT, low-vol tercile, Sharpe=-1.351

**Zero cells passed across the entire grid.**

## Root cause: signal starvation

Trade counts over the full 2019-2026 sample (default params: profile_window=20, vol_expansion_mult=1.3):

| Symbol | Trades over ~7.5 years |
|---|---|
| QQQ | 1 |
| SPY | 2 |
| BTC/USDT | 12 |
| ETH/USDT | 10 |

The compound filter (VAL reclaim AND bullish engulfing AND volume
expansion, all on the SAME bar) is so restrictive that it produces
statistically meaningless sample sizes on equity (1-2 trades total) and
still very thin samples on crypto (10-12 trades). This isn't a "the edge
doesn't exist" rejection so much as "the exact same-bar compound
confirmation is too strict to ever fire meaningfully" -- the opposite
problem from 2026-09-10-001 (which fired too often on weak signals).

## Decision: REJECT (signal starvation, not a proper edge test)

Did not proceed to Step 7 single-config validators given the grid's
decisive 0/48 pass fraction and the trade-count evidence showing the
compound filter essentially never fires. No amount of single-config
validator-running would change this conclusion.

**Notes for a future iteration:** the source's OWN indicator only requires
the engulfing candle OR volume expansion to occur "within a bounded
window" following the breakout, not necessarily on the exact same bar as
the reclaim -- this strategy's implementation required all conditions
simultaneously on one bar, which is stricter than the source's own
disclosed rule. A future iteration could relax this to "engulfing +
volume expansion within N bars after the VAL reclaim" (a proper lagged
confirmation window matching the source's "Maximum bars to signal after
breakout" setting) rather than requiring same-bar coincidence, which would
likely produce a usable trade count while still filtering fakeouts.
