# Backtest Report: Intraday Range-Efficiency Trend Regime Gate

**Strategy file:** `strategies/2026-09-27_range_efficiency_trend_regime.py`
**Date:** 2026-09-27
**Source:** thetrading.tools, "Range Efficiency: Is QQQ Trending or
Chopping?" (https://www.thetrading.tools/range-efficiency, read via
browser_exec this iteration).

## Hypothesis

Per-bar range efficiency = |close-open| / (high-low) measures how much of a
day's intraday range converted into net directional progress. A rolling
50-day average of this ratio is used by the source as a trend-vs-chop
regime gauge. Adapted here: gate a standard SMA trend-following signal to
only take/hold long exposure while the rolling average range-efficiency is
above a threshold (source's own disclosed QQQ all-time average ~0.474).

## Single-config metrics (QQQ, trend_window=50, eff_threshold=0.40 -- the
grid's best-passing cell)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.013 | >= 1.0 | pass |
| Max drawdown | 0.189 | <= 0.25 | pass |
| Transaction cost survival | 0.776 net Sharpe (208 trades, 10bps/trade) | >= 0.5 | pass |
| Walk-forward | not computed (vectorbt.utils.splitting API mismatch in this environment's vectorbt version -- known infra limitation, not specific to this strategy) | >= 0.75 | skipped |
| Parameter sensitivity | 1.449 relative std | <= 0.5 | **FAIL** |

Parameter sensitivity was computed directly from the grid's 6
trend_window x eff_threshold cells' Sharpe values (0.890, 0.486, -0.323,
1.013, 0.416, -0.313) per Step 7's guidance to derive it from the grid
rather than a separate sweep. The relative standard deviation across these
six adjacent parameter combinations is 1.449 -- far above the 0.5
threshold -- because Sharpe flips from solidly positive (eff_threshold=0.40)
to solidly negative (eff_threshold=0.55) within a narrow, economically
reasonable parameter range. This means the single passing config
(trend_window=50, eff_threshold=0.40) is a fragile local optimum rather
than a robust edge: a small change to the regime threshold (e.g. 0.474,
the source's own stated headline "all-time average" value) drops Sharpe to
0.416 and 0.55 flips it fully negative.

## Grid summary (Step 6)

- Param grid: `trend_window` in {20, 50}, `eff_threshold` in {0.40, 0.474,
  0.55}
- Symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits=3
- Total cells: 72; **passed: 10 (pass_fraction 0.139)**
- By asset class: equity 9/36, crypto 1/36.
- By vol regime: low 6/24, mid 4/24, high 0/24 (never passes in high-vol
  regimes).
- Best cell: crypto ETH/USDT, trend_window=50, eff_threshold=0.40, mid-vol,
  Sharpe 1.996.
- Worst cell: crypto ETH/USDT, trend_window=50, eff_threshold=0.474,
  low-vol, Sharpe -0.778.

## Decision: REJECT

Single-config Sharpe/MDD/transaction-cost-survival all pass at the grid's
one best-performing config, BUT parameter sensitivity fails decisively
(relative std 1.449 vs 0.5 threshold) -- the edge is highly fragile to the
eff_threshold parameter specifically, flipping sign within the tested
range including at the source's own disclosed headline average value
(0.474). Per Step 8, any validator failing means reject. Strategy file
kept in `strategies/` as a record of a rejected (parameter-fragile)
attempt.
