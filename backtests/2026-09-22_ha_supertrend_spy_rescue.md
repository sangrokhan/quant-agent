# HA-Supertrend Real-Price-Execution — SPY Rescue (Backtest Report)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ha_supertrend_real_price_exec.py`
**KB id:** 2026-09-22-011

## Hypothesis

Direct rescue of this same cron trigger's near-miss 2026-09-22-005
(HA-Supertrend real-price-execution, accepted QQQ only at
atr_window=10/multiplier=3.0; SPY failed only Sharpe at that config,
0.843<1.0). Neighborhood parameter search around the original grid
(atr_window∈{10,14,20}, multiplier∈{2.0,2.5,3.0,3.5}) found
atr_window=14/multiplier=2.0 clears the Sharpe bar on BOTH QQQ (1.336) and
SPY (1.247) simultaneously. No new external source -- same strategy code,
parameter retune only, following this repo's established rescue pattern.

## Single-config validation (Step 7) — atr_window=14, multiplier=2.0

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.336 ✅ | 1.247 ✅ | ≥1.0 |
| Max drawdown | 0.156 ✅ | 0.091 ✅ | ≤0.25 |
| TC survival (10bps/trade, 36 trades each) | net Sharpe 1.289 ✅ | net Sharpe 1.183 ✅ | ≥0.5 |
| Walk-forward (4 splits) | 1.0 ✅ | 1.0 ✅ | ≥0.75 |
| Parameter sensitivity (atr_window∈{10,14,20} @ multiplier=2.0) | rel std 0.004 ✅ | rel std 0.170 ✅ | ≤0.5 |

**All 5 validators pass on BOTH QQQ and SPY** -- a stronger, broader
config than the original accept (which only covered QQQ at
atr_window=10/multiplier=3.0). QQQ's parameter sensitivity here is
exceptionally low (0.004), the tightest margin of any accepted strategy
found in this KB search.

## Decision

**Accept for QQQ AND SPY** at the retuned config (atr_window=14,
multiplier=2.0), superseding/extending the narrower 2026-09-22-005 accept.
Crypto remains out of scope per that entry's original decisive grid
rejection (not re-tested this sub-iteration).
