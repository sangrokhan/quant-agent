# 2026-09-23 TRIX Signal-Line Crossover + 50/200 EMA Trend Regime Filter (SPY/QQQ/BTC/ETH)

## Hypothesis
Source: Google AI Overview (Korean-language SERP; search: "TRIX indicator
signal line crossover trading strategy specific parameters backtest"), read
via browser_exec Google SERP fallback (web_search DDGS backend errored this
query). `suggested_workload=light` this iteration.

Rule: TRIX(14) crossing above its 9/12-period signal-line EMA, confirmed
by price being above both a 50 EMA and 200 EMA (bullish trend regime);
exit on the reverse (dead) cross.

## Grid test summary (trix_window x [14,21], signal_window x [9,12];
symbols QQQ equity, BTC/USDT crypto; vol_regime_splits=3; 24 total cells)

- pass_fraction: 0.375 (9/24) -- the strongest of this cron trigger's 4
  candidates so far
- by_asset_class: equity 4/12, crypto 5/12
- by_vol_regime: low 7/8 (0.875!), mid 1/8, high 1/8
- best_cell: trix_window=14, signal_window=12, equity QQQ, low-vol,
  Sharpe 2.27
- worst_cell: trix_window=14, signal_window=12, equity QQQ, high-vol,
  Sharpe -0.76

## Single-config validation (full-period, unconditional, best param combo
per symbol from a widened sweep incl. SPY/ETH and alternate EMA pairs)

| Symbol | trix/signal | fast/slow EMA | Sharpe | Passed (>=1.0) | Max DD | Passed (<=0.25) |
|--------|-------------|----------------|--------|------------------|--------|--------------------|
| SPY    | 14/12       | 50/100-150     | 0.983  | No (near-miss)   | 0.136  | Yes |
| SPY    | 14/12       | 50/200 (base)  | 0.946  | No               | 0.136  | Yes |
| QQQ    | 14/12       | 50/200 (base)  | 0.724  | No               | 0.181  | Yes |
| BTC    | 14/9        | 50/200 (base)  | 0.283  | No               | 0.376  | No |
| ETH    | 14/9        | 50/200 (base)  | 0.324  | No               | 0.255  | No |

Widened EMA regime-filter sweep (fast/slow in {(20,50),(30,100),(50,100),
(50,150),(50,200)}) found the best achievable full-period SPY Sharpe was
0.983 (fast=50, slow=100 or 150) -- a very close near-miss just under the
1.0 threshold, but did not clear it in any tested configuration.

## Verdict: REJECTED (near-miss, strongest candidate this cron trigger)

No tested config/symbol combination clears the full-period Sharpe >= 1.0
gate (best 0.983 on SPY). However this is the strongest signal-to-noise
result of this trigger's 4 iterations: an 0.875 pass rate specifically in
the LOW-vol tercile (vs. the crossover-with-regime-filter pattern seen
repeatedly in this KB -- trend strategies working well in calm regimes,
poorly in choppy/high-vol ones). Walk-forward/tx-cost/parameter-sensitivity
validators skipped given the light workload and the clear (if narrow)
full-period miss.

Strategy file kept in `strategies/` as a rejected-but-promising record.
**Explicitly worth revisiting**: bake the low-vol regime membership directly
into the entry condition (as `2026-09-03_bb_meanrev_qqq_volregime.py` does)
rather than only using it as a post-hoc grid-cell breakdown -- an
EMA-trend-filter TRIX crossover that ALSO requires being in the low-vol
tercile at entry time could plausibly clear the full-period Sharpe bar,
since the 0.875 low-vol pass rate strongly suggests most of the drag comes
from mid/high-vol whipsaw periods diluting the average.
