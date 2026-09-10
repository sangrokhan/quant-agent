# Backtest Report: TTM Trend Color-Flip + Realized-Vol Regime Gate (follow-up)

**Date:** 2026-09-10
**Strategy file:** `strategies/2026-09-10_ttm_trend_colorflip_volgate.py`
**Status:** REJECTED (vol gate made the near-miss WORSE, not better)

## Hypothesis

Direct follow-up to near-miss 2026-09-10-080 (plain TTM Trend color-flip +
SMA trend filter, accepted SPY only, QQQ full-sample Sharpe 0.916 vs
threshold 1.0). That entry's grid summary showed edge concentrated in the
low-vol tercile (12/24 passing cells vs mid 2/24, high 1/24), matching the
regime-dependence pattern that has rescued several other near-misses in
this repo via an explicit realized-vol gate (e.g.
2026-09-03_bb_meanrev_qqq_volregime.py, 2026-09-08-043). This variant adds
that same vol-gate construction (20d realized vol <= trailing 252d
median) as BOTH an entry precondition and a new exit trigger (flatten
immediately if the regime flips to high-vol), keeping the TTM Trend
color-flip + SMA trend-filter logic otherwise identical.

## Results (full sample, 2019-01-01 to 2026-09-01)

| Validator | QQQ (parent 2026-09-10-080) | QQQ (this vol-gated variant) | SPY (parent) | SPY (this variant) |
|---|---|---|---|---|
| Sharpe ratio | 0.916 (near-miss) | **0.616 (worse)** | 1.155 (pass) | **0.332 (worse, now fails)** |
| Max drawdown | 0.194 | 0.082 | 0.095 | 0.107 |
| TC survival | 0.747 pass | **0.430 FAIL** | 0.912 pass | **0.085 FAIL** |
| Walk-forward | 0.75 pass | 0.75 pass | 0.75 pass | **0.50 FAIL** |
| Param sensitivity | 0.433 pass | 0.117 pass | 0.419 pass | 0.191 pass |
| Trade count | (not directly comparable, different exit logic) | 68 | -- | 85 |

## Step 8 — Decision: REJECT

The vol-gate follow-up made every metric WORSE, not better, on both
symbols -- the opposite of the intended fix. The added regime-flip exit
condition (flatten immediately when 20d realized vol crosses above its
trailing median) roughly doubled trade frequency vs the parent's simpler
color-flip/trend-filter exit logic (68/85 trades vs the parent's much
lower implied count), which crushed transaction-cost survival on both
symbols and actively HURT the previously-accepted SPY config (Sharpe
1.155 -> 0.332, now itself failing). This is a useful negative result:
unlike the Bollinger-mean-reversion and VQI cases where a vol regime gate
rescued a near-miss, here TTM Trend's underlying edge is apparently NOT
concentrated by inherently choppy high-vol whipsaws in a way a vol gate
fixes -- instead the gate's own regime-flip exits introduce MORE
whipsaw-driven turnover than the color-flip signal alone, net-negative
after costs. The grid's low-vol-tercile-only cell-level promise from the
parent entry did not translate into a working gated strategy at
full-sample scale.

The already-accepted parent strategy
(`strategies/2026-09-10_ttm_trend_colorflip.py`, SPY-only) remains live
and unaffected by this rejected follow-up. This variant's file and report
are kept as a record of a rejected attempt.
