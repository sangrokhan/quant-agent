# Bull Flag Pole-Breakout — Backtest Report (REJECTED)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_bull_flag_pole_breakout.py`
**Knowledge base id:** 2026-09-08-130

## Hypothesis

Per https://www.warriortrading.com/bull-flag-trading/'s disclosed mechanical
rule: a "flagpole" (strong up-move on above-average volume) followed by a
"flag" (shallow 2-5 candle pullback not retracing more than 50% of the pole)
resolving in a breakout above the flag's own high is a high-probability
continuation setup; stop at the flag's low, 2:1 reward:risk target. Adapted
from the source's intraday day-trading framing to daily bars. Distinct from
every other consolidation-breakout construction already in this repo
(Rectangle, Rising Three Methods, Ascending/Falling Wedge/Triangle — none
of which use a discrete flagpole-move-size + 50%-retracement-cap rule).

## Grid test summary (validation/grid_test.py)

- Grid: `pole_min_return` in {0.02,0.03}, `pole_vol_mult`=1.0,
  `retrace_cap`=0.5, `reward_risk`=2.0, `max_hold_days`=15 (2 combos) ×
  {QQQ, SPY, BTC/USDT, ETH/USDT} × 3 vol-regime terciles = 24 cells.
- **pass_fraction: 0.042** (1/24) — decisive reject
- by_asset_class: equity 1/12; **crypto 0/12**
- by_vol_regime: low 1/8; mid 0/8; high 0/8
- best_cell: QQQ, pole_min_return=0.02, low-vol regime, Sharpe 1.61 (isolated)

## Single-config full-sample check (best config: pole_min_return=0.02,
pole_vol_mult=1.0, retrace_cap=0.5, reward_risk=2.0, max_hold_days=15)

| Metric | QQQ | SPY |
|---|---|---|
| Full-sample Sharpe | 0.732 | 0.612 |
| Max drawdown | 0.203 | 0.153 |
| Num trades | 42 | 27 |

Both fail the Sharpe >= 1.0 threshold decisively. Given the grid's
pass_fraction is already only 0.042 (a single isolated low-vol cell) and
full-sample Sharpe misses by a wide margin on both equities, the remaining
validator suite (TC-survival, walk-forward, parameter sensitivity) was
skipped per Step 7's minimum-subset guidance for a clearly-failing config.

## Decision: REJECTED

The mechanical daily-bar adaptation of an intraday day-trading pattern
(bull flag pole + shallow pullback + breakout) shows very sparse, weak
signal on daily bars — likely because the source's own rule is tuned for
1-5 minute intraday charts where flagpoles/pullbacks/breakouts happen
within a single session, not the multi-day structures this daily-bar
adaptation searches for. Crypto rejected decisively (0/12 grid cells).
Not recommended for revisiting without intraday (sub-daily) OHLCV data,
which this repo's loaders do not currently provide for equities.
