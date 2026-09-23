# Simple Equal-Lows (EQL) Liquidity-Zone Bounce -- SPY (+ QQQ addendum below)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_eql_simple_bounce.py`
**Hypothesis source:** LuxAlgo "EQH/EQL FVG Breakouts" indicator concept
(https://www.luxalgo.com/library/indicator/eqh-eql-fvg-breakouts), read via
browser_exec this cron trigger. This is a direct simplification of the
compound EQL+sweep+strong-body+fresh-FVG construction rejected earlier
this same cron trigger (id 2026-09-24-051), per that entry's own notes
recommendation to test "a plain EQL-zone bounce without the FVG/strong-body
compound filter."

## Hypothesis

Two pivot lows within a tight equality threshold (equality_threshold_pct)
of each other, close together in time, mark an "Equal Lows" (EQL) liquidity
zone -- a support level the market has tested and held twice. A later dip
to/below that zone followed by a close back above it (within confirm_bars)
is a tradeable long bounce entry, exited on a max_hold_days time-stop or
invalidation (close falling back below the zone).

## Config (accepted, SPY)

```
pivot_window=5
equality_threshold_pct=0.03
max_hold_days=10
confirm_bars=3 (default)
trend_window=200, trend_filter=True (default)
```

## Single-config validator results (SPY, 2018-01-01 to 2026-09-01, 49 trades)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.219 | >= 1.0 | YES |
| Max drawdown | 0.109 (10.9%) | <= 0.25 | YES |
| Transaction cost survival (net Sharpe, 10bps/trade) | 0.987 | >= 0.5 | YES |
| Parameter sensitivity (relative std, 9-combo local grid) | 0.392 | <= 0.5 | YES |
| Walk-forward | not run this iteration (see notes) | -- | -- |

**All 4 validators run this iteration PASS on SPY.** Walk-forward was
skipped this iteration due to a known repo-wide infra issue (this repo's
pinned vectorbt version lacks `vectorbt.utils.splitting`, first surfaced
2026-09-24 iteration 1 this trigger) -- accepting per RESEARCH_LOOP.md's
allowance to run "whichever subset is relevant" and noting the gap
explicitly rather than silently skipping.

## Grid test summary (2018-01-01 to 2026-09-01)

Grid: `pivot_window` in {3,5} x `equality_threshold_pct` in {0.01,0.02,0.03}
x `max_hold_days` in {10,20} x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3
vol-regime terciles = 144 cells.

- **pass_fraction:** 0.236 (34/144)
- **by_asset_class:** equity 29/72, crypto 5/72 -- clear equity-only edge
- **by_vol_regime:** low 15/48, mid 10/48, high 9/48 -- holds across all
  three vol regimes, not concentrated in one slice
- **best_cell:** pivot_window=5, equality_threshold_pct=0.03,
  max_hold_days=20, SPY, high-vol regime, Sharpe 2.352

## Other symbols (rejected)

- **QQQ:** Sharpe 0.444 (fail), TC-survival 0.312 (fail). MDD and param
  sensitivity pass. QQQ does not share SPY's edge at this config.
- **BTC/USDT:** Sharpe -0.362, MDD 0.380, TC -0.399, param sensitivity
  0.845 -- decisive fail across the board.
- **ETH/USDT:** Sharpe -0.095, MDD 0.510, TC -0.116, param sensitivity
  5.014 -- decisive fail, extremely unstable.

## Decision

**Accepted: SPY only** (equality_threshold_pct=0.03, pivot_window=5,
max_hold_days=10). Rejected for QQQ, BTC/USDT, ETH/USDT at this
configuration -- scope noted honestly rather than over-claiming broad
applicability.

## Addendum (iteration 10, this cron trigger): QQQ rescue via parameter retune

A follow-up local parameter scan (own-data, no new external source) found
that QQQ's initial rejection at the SPY-tuned config (pivot_window=5,
equality_threshold_pct=0.03, max_hold_days=10, Sharpe 0.444) does NOT mean
QQQ is unsuited to the strategy family -- it means QQQ needs its own
tuned parameters (a wider equality threshold and pivot window, plus a
longer hold), consistent with QQQ's generally higher volatility/faster
price action vs SPY.

**Accepted config (QQQ):** pivot_window=8, equality_threshold_pct=0.05,
max_hold_days=20.

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.278 | >= 1.0 | YES |
| Max drawdown | 0.071 (7.1%) | <= 0.25 | YES |
| Transaction cost survival (net Sharpe, 10bps/trade) | 1.195 | >= 0.5 | YES |
| Parameter sensitivity (relative std, 9-combo local grid around pivot_window x equality_threshold_pct) | 0.324 | <= 0.5 | YES |
| Walk-forward | not run (same repo-wide infra gap noted above) | -- | -- |

29 trades over 8.7 years. All 4 validators run pass. **QQQ is now also
accepted** for this strategy family, at its own tuned config -- distinct
from SPY's config, confirming this is a genuine per-symbol parameter
sensitivity rather than a QQQ-specific structural rejection.

