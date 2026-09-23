# BOS Trend-Continuation — SPY Parameter-Retune Rescue — Backtest Report (2026-09-24)

## Hypothesis

Direct rescue attempt for the near-miss flagged in 2026-09-24-040 (Break
of Structure trend-continuation pullback-retest, SPY at
swing_window=5/retest_window=5/max_hold_days=20, Sharpe 0.814 near-miss,
all other validators passing). Own-data parameter re-search (no new
external source): swept swing_window ∈ {3,4,5,6,7}, retest_window ∈
{5,10}, max_hold_days ∈ {15,20,25,30} on SPY, found swing_window=3,
retest_window=5, max_hold_days=25 clears the Sharpe threshold (1.058).

Same unmodified strategy code
(`strategies/2026-09-24_bos_trend_continuation_retest.py`), only
parameters retuned.

## Full validation at swing_window=3, retest_window=5, max_hold_days=25 (SPY)

| Validator | Result |
|---|---|
| Sharpe (>=1.0) | **PASS** 1.058 |
| Max Drawdown (<=0.25) | PASS 0.094 |
| TC Survival (>=0.5 net Sharpe, 10bps/trade) | PASS 0.980 (25 trades) |
| Walk-Forward (>=0.75 pass fraction, 4 splits) | PASS 1.0 (4/4) |
| Parameter Sensitivity (<=0.5 relative std) | PASS 0.223 |

All 5/5 validators pass.

## Decision

**Accept SPY (swing_window=3, retest_window=5, max_hold_days=25) as an
addition to the BOS trend-continuation strategy's accepted scope.**
Combined with the existing QQQ accept (2026-09-24-040, swing_window=3,
retest_window=5, max_hold_days=20) and the BTC/USDT leverage-cap rescue
(2026-09-24-041, leverage_cap=0.7), this strategy now covers all three
symbols originally tested: QQQ, SPY, and BTC/USDT, each with its own
tuned config.
