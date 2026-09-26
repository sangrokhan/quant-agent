# Backtest Report: Drop-Base-Rally (DBR) Demand Zone

**Strategy file:** `strategies/2026-09-26_drop_base_rally_demand_zone.py`
**Hypothesis id:** 2026-09-26-053
**Source:** https://algobars.com/strategy-templates/supply-demand/drop-base-rally/
(and category overview: https://algobars.com/strategy-templates/supply-demand/)

## Hypothesis

A sharp decline into a narrow 1-6 candle consolidation base, followed by a
rally leg at least 2x the base's own range, marks a fresh institutional
demand zone (the base's high-low price band). The first time price later
returns to touch that zone, a bullish reversal bar there signals a
high-probability long entry; stop below the zone low, target a
measure-rule multiple of the zone height above the zone top.

This is a two-phase pattern (zone *formation*, followed by a separate,
possibly much later, zone *retest*) distinct from every prior strategy in
this repo:
- Donchian role-reversal retest (2026-09-17-175): a single price *level*
  (N-day high), immediate retest, no separate multi-bar consolidation
  base.
- Pothole (2026-09-24-109): dip-and-recover in one continuous move, no
  later delayed retest of a previously-formed zone.

## Single-config validator results (QQQ, 2018-01-01 to 2026-09-01)

Config: `decline_pct=0.03, rally_mult=1.5, target_rr=1.5, max_hold_days=40`

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.794 | >= 1.0 | ✅ |
| Max drawdown | 2.3% | <= 25% | ✅ |
| Transaction cost survival (net Sharpe @ 10bps/trade, 7 trades) | 1.749 | >= 0.5 | ✅ |
| Walk-forward | skipped | n/a | — (repo-wide `vectorbt.utils.splitting` API issue) |
| Parameter sensitivity (relative std across 6 nearby configs) | 0.040 | <= 0.5 | ✅ |

**Caveat:** only 7 completed trades over the ~8.7-year sample — a thin
sample that clears every numeric threshold cleanly but should be treated
with appropriate skepticism for true out-of-sample robustness.

## Grid summary (Step 6)

Grid: `decline_pct in [0.03, 0.05, 0.08] x rally_mult in [1.5, 2.0, 3.0] x
target_rr in [1.5, 2.0, 3.0] x max_hold_days in [20, 40]`, symbols
`equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]`, `vol_regime_splits=3`.

```json
{
  "total_cells": 648,
  "passed_cells": 104,
  "pass_fraction": 0.160,
  "by_asset_class": {
    "equity": {"passed": 41, "total": 324},
    "crypto": {"passed": 63, "total": 324}
  },
  "by_vol_regime": {
    "low": {"passed": 71, "total": 216},
    "mid": {"passed": 17, "total": 216},
    "high": {"passed": 16, "total": 216}
  }
}
```

The signal is heavily concentrated in **low-volatility regimes** for both
asset classes — a caveat for future loops not to over-trust this strategy
during high-vol conditions. QQQ was the strongest and most consistent
symbol (passing 3/6 nearby configs across all three vol regimes
simultaneously); SPY passed only 2/6; crypto passed a higher raw cell
count but concentrated almost entirely in the low-vol tercile and was not
run through the full single-config validator suite this iteration.

## Decision

**Accepted for QQQ only.** SPY and crypto (BTC/USDT, ETH/USDT) are left as
grid-only candidates for a future iteration's dedicated retune/validation
pass, not accepted or rejected outright this iteration.
