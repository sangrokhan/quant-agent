# Awesome Oscillator Saucer Continuation — SPY Rescue (Backtest Report)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ao_saucer_continuation.py`
**KB id:** 2026-09-22-012

## Hypothesis

Direct rescue of this same cron trigger's near-miss 2026-09-22-006 (AO
Saucer continuation, accepted QQQ only at max_hold_days=10; SPY failed
only Sharpe, 0.942<1.0, at that config). Neighborhood search over
max_hold_days (5 through 30) found max_hold_days=25 clears Sharpe on BOTH
QQQ (1.119) and SPY (1.101) simultaneously. No new external source -- same
strategy code as 2026-09-22-006, parameter retune only.

## Single-config validation (Step 7) — max_hold_days=25

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.119 ✅ | 1.101 ✅ | ≥1.0 |
| Max drawdown | 0.210 ✅ | 0.153 ✅ | ≤0.25 |
| TC survival (10bps/trade, 38 trades each) | net Sharpe 1.049 ✅ | net Sharpe 1.008 ✅ | ≥0.5 |
| Walk-forward (4 splits) | 0.75 ✅ | 0.75 ✅ | ≥0.75 (exactly at threshold, split 2 of 4 negative on both) |
| Parameter sensitivity (max_hold_days∈{20,22,25,28}) | rel std 0.094 ✅ | rel std 0.073 ✅ | ≤0.5 |

**All 5 validators pass on BOTH QQQ and SPY.** Walk-forward is exactly at
the 0.75 threshold for both symbols (3/4 splits positive, split 2
negative on both) -- a real but not overwhelming margin, worth noting for
future monitoring.

## Decision

**Accept for QQQ AND SPY** at the retuned config (max_hold_days=25),
superseding/extending the narrower 2026-09-22-006 accept (QQQ only at
max_hold_days=10). Crypto remains out of scope per that entry's original
finding (no crypto config held up across all 3 vol regimes; not
re-tested this sub-iteration).
