# 2026-09-20: Fibonacci Retracement Pullback — Rescue Attempt of Near-Miss 2026-09-03-022 — REJECTED

**Background:** 2026-09-03-022 (Fibonacci 50-78.6% retracement pullback-buy
in a confirmed uptrend, per quantifiedstrategies.com) was a near-miss:
QQQ Sharpe 0.916 at swing_lookback=20/retrace_high=0.786, only an 8%
shortfall vs the 1.0 threshold, with MDD/TC-survival/param-sensitivity all
passing. This iteration attempts a direct parameter retune rescue of that
near-miss using the existing strategy file
(`strategies/2026-09-03_fibonacci_retracement_pullback.py`), no new
external source.

**Grid retune** (trend_window in [150,200], swing_lookback in
[15,20,30,40,60], retrace_low in [0.5,0.618], retrace_high in
[0.618,0.786], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles, 480 cells):
- pass_fraction: 0.067 (32/480)
- by_asset_class: equity 32/240, crypto **0/240**
- by_vol_regime: low 15/160, mid 12/160, high 5/160
- best_cell: SPY low-vol, sharpe 2.15 (trend_window=200, swing_lookback=15,
  retrace_low=0.5, retrace_high=0.786)

**Full-sample confirmation** across 8 configs tried (QQQ/SPY):

| Config | QQQ Sharpe | SPY Sharpe |
|---|---|---|
| tw=200,sl=15,0.5-0.786 | 0.704 | 0.493 |
| tw=150,sl=20,0.5-0.786 | **0.965** | 0.638 |
| tw=200,sl=20,0.618-0.786 | 0.612 | 0.676 |
| tw=150,sl=25,0.5-0.786 | 0.742 | 0.696 |
| tw=120,sl=20,0.5-0.786 | 0.781 | 0.827 |
| tw=150,sl=20,0.5-0.7 | 0.869 | 0.514 |
| tw=150,sl=18,0.5-0.786 | **0.965** | 0.659 |

Best achieved: QQQ Sharpe 0.965 (trend_window=150, swing_lookback=18 or 20,
retrace 0.5-0.786) -- still below the 1.0 threshold, and SPY never exceeds
0.827 across any config tried in this rescue attempt.

**Decision: REJECTED (rescue unsuccessful).** Widening/narrowing
swing_lookback, trend_window, and the retracement zone bounds could not
push QQQ's full-sample Sharpe above 1.0 (best 0.965, essentially unchanged
from the original 0.916 near-miss) nor SPY meaningfully closer (best
0.827). The grid confirms 0/240 crypto cells pass at any parameter
combination. This near-miss appears to be a genuine, stable ceiling around
Sharpe ~0.9-1.0 for QQQ rather than a parameter-tuning artifact -- flagged
as NOT further reviveable via simple parameter retuning; a future attempt
would need a structurally different entry/exit rule (e.g. added volume or
RSI confirmation at the retracement zone, per some sources' "wait for
reversal confirmation" refinement) rather than just widening windows.

Strategy file unchanged (still the original, no live acceptance change).
