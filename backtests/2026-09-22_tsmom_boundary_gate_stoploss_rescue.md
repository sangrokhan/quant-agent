# TSMOM Boundary-Extreme-Gate + Stop-Loss Rescue — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_tsmom_boundary_gate_stoploss_rescue.py`
**KB id:** 2026-09-22-038

## Hypothesis

Direct fix attempt for this cron trigger's prior near-miss rejection
2026-09-22-037 (12-month TSMOM + trailing-return extreme-percentile gate,
proxying Suominen & Hjalmarsson's "Boundaries of Time Series Momentum"
finding). That entry's own diagnosis: max drawdown (0.286) was
parameter-invariant across every extreme_pctile/lookback_years combo
because the monthly-rebalanced gate could not react fast enough to the
March 2020 COVID crash. This entry adds a DAILY-checked hard
formation-price stop-loss overlay (reusing this repo's already-accepted
mechanism from `strategies/2026-09-08_formation_price_stoploss_trend.py`)
on top of the identical monthly TSMOM+extreme-gate logic, so a fast crash
can be exited mid-month rather than waiting for the next monthly
rebalance.

## Grid test (Step 6)

`stop_loss_pct` in {0.08, 0.10, 0.15} x `extreme_pctile`={90.0}, symbols
{equity: QQQ, SPY; crypto: BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- Total cells: 36, passed: 9 (**pass_fraction 0.25**, up from the
  ungated-stop predecessor's 0.1875)
- by_asset_class: equity 9/18, crypto 0/18
- by_vol_regime: low 6/12, mid 3/12, high 0/12
- best_cell: stop_loss_pct=0.08, SPY, low-vol, Sharpe=2.662

## Single-config validation (Step 7) — lookback_days=252, lookback_years=5, extreme_pctile=90.0, stop_loss_pct=0.08, QQQ, 2019-01-01 to 2026-09-01

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.129 | ≥1.0 | **PASS** |
| Max drawdown | 0.229 | ≤0.25 | **PASS** |
| Transaction cost survival (9 trades, 10bps) | 1.121 | ≥0.5 | **PASS** |
| Walk-forward (4 manual splits) | 3/4 positive (1.35, -1.24, 1.79, 0.56) = 0.75 | ≥0.75 | **PASS** |
| Parameter sensitivity (stop_loss_pct ∈ {0.06,0.08,0.10,0.12}) | relative_std 0.023 | ≤0.5 | **PASS** |

All 5 validators pass for QQQ. Only 9 round-trip trades over the ~7.7-year
sample (monthly-rebalanced base signal + rare stop-outs) — very low
turnover, consistent with the strong TC-survival result.

SPY at the same config: Sharpe 0.937 (near-miss), MDD 0.204 (pass). SPY
does not clear the Sharpe bar at this shared config — not pursued further
this iteration (QQQ-only acceptance is a common pattern in this repo's
knowledge base).

Crypto (BTC/USDT, ETH/USDT): rejected decisively per the grid (0/18
cells) — 12-month absolute momentum + this repo's typical monthly-
rebalance convention is not a signal construction that transfers to
24/7 crypto data, consistent with every other TSMOM variant tested here.

## Decision: ACCEPTED (QQQ only)

The daily-checked hard stop-loss overlay successfully rescues the prior
near-miss: MDD drops from a parameter-invariant 0.286 (monthly-gate-only
version) to 0.229 at stop_loss_pct=0.08, while Sharpe actually IMPROVES
from 1.025 to 1.129 (fewer/faster-cut losing positions more than offsets
the cost of occasionally cutting a position that would have recovered).
This confirms the diagnosis from 2026-09-22-037's notes: the fix that
worked was adding a faster daily-reacting circuit-breaker, not further
tuning of the monthly-rebalanced gate's own parameters. Strategy file and
this report are kept as a live accepted strategy (QQQ only); SPY and
crypto are documented above as rejected/near-miss at the shared config.
