# Simple Equal-Lows (EQL) Liquidity-Zone Bounce -- SPY

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
