# BOS Trend-Continuation — BTC/USDT Leverage-Cap Rescue — Backtest Report (2026-09-24)

## Hypothesis

Direct rescue attempt for the near-miss flagged in this same cron
trigger's prior iteration (2026-09-24-040, Break of Structure
trend-continuation pullback-retest strategy): BTC/USDT at
swing_window=3/retest_window=5/max_hold_days=30 passed a perfect 3/3
grid vol-regime test and Sharpe 1.292, but failed the single-config Max
Drawdown validator (0.280 vs 0.25 threshold) despite a max_hold_days sweep
not fixing it. This iteration applies this repo's established
leverage-cap-recalibration rescue pattern (previously successful for
Elder-Ray, Chaikin Oscillator, Twiggs Money Flow, and Ultimate Oscillator
crypto MDD failures): reducing `leverage_cap` scales exposure down
proportionally, which reduces MDD roughly linearly while leaving the
(already leverage-invariant) Sharpe ratio essentially unchanged, since
Sharpe is scale-invariant for a fixed strategy but MDD is not.

Same unmodified strategy code
(`strategies/2026-09-24_bos_trend_continuation_retest.py`), only
`leverage_cap` swept.

## Rescue sweep

| leverage_cap | Sharpe | MDD |
|---|---|---|
| 1.0 (baseline, prior iteration) | 1.292 | 0.280 (FAIL) |
| 0.5 | 1.292 | 0.147 |
| 0.6 | 1.292 | 0.175 |
| 0.7 | 1.292 | 0.202 (PASS) |
| 0.8 | 1.292 | 0.229 (PASS) |

`leverage_cap=0.7` chosen as the largest exposure that clears the 0.25 MDD
threshold with margin.

## Full validation at leverage_cap=0.7 (BTC/USDT, swing_window=3, retest_window=5, max_hold_days=30)

| Validator | Result |
|---|---|
| Sharpe (>=1.0) | **PASS** 1.292 |
| Max Drawdown (<=0.25) | **PASS** 0.202 |
| TC Survival (>=0.5 net Sharpe, 10bps/trade) | PASS 1.272 (25 trades) |
| Walk-Forward (>=0.75 pass fraction, 4 splits) | PASS 1.0 (4/4) |
| Parameter Sensitivity (<=0.5 relative std) | PASS 0.078 |

All 5/5 validators pass.

## Decision

**Accept BTC/USDT (leverage_cap=0.7) as an addition to the existing BOS
trend-continuation strategy's accepted scope** (previously QQQ only, per
2026-09-24-040). This is the same strategy file, same mechanism, rescued
via a documented leverage-cap parameter rather than a new strategy design
-- logged as a distinct knowledge-base entry per this repo's convention
for rescue attempts (references the prior near-miss id).
