# 2026-09-11 SVXY VIX/VIX3M Term-Structure Contango Strategy — Backtest Report

**Hypothesis:** Long SVXY (short-vol ETF) when VIX/VIX3M ratio <= contango_thresh
(contango regime), flat during backwardation (ratio > thresh), with a
min_hold_days re-entry buffer after a backwardation flip. Source:
https://www.backtesteverything.com/blog/backtesting-vix-term-structure-volatility-etfs
(visited this iteration via browser_exec, web_extract failed — DDGS backend
cannot extract URL content).

Source's own headline claim: short VXX/long SVXY during contango returned
~28% annualized (2011-2024) before borrow costs, Sharpe 0.95, **but with a
42% max drawdown during the Feb 2018 "Volmageddon" event** — the source
itself frames this as the central risk of the trade, recommending only
35-40% portfolio allocation to survive it.

## Single-config validators (best full-sample config: contango_thresh=1.0, min_hold_days=1, SVXY, 2018-01-01 to 2024-01-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.639 | >= 1.0 | **FAIL** |
| Max drawdown | 0.402 | <= 0.25 | **FAIL** |

Transaction-cost/walk-forward/parameter-sensitivity validators skipped —
already decisively rejected on the first two.

## Step 6 grid summary (contango_thresh in [0.95,1.0,1.05] x min_hold_days in [1,3,5], SVXY only, vol_regime_splits=3)

- 27 total cells, 9 passed (pass_fraction 0.333)
- **by_asset_class**: equity 9/27 (33%) — crypto N/A (VIX has no crypto analog)
- **by_vol_regime**: low 9/9 (100% pass), mid 0/9, high 0/9
- Best cell: contango_thresh=1.0, min_hold_days=1, low-vol regime, Sharpe 2.33
- Worst cell: contango_thresh=0.95, min_hold_days=3, high-vol regime, Sharpe -1.44

The grid confirms the strategy's edge (as the source itself concedes) is
**entirely confined to calm/low-vol regimes** — it decisively fails in
mid and high volatility regimes, which is precisely when a
backwardation-flip-driven strategy MUST perform to be tradeable (the
whole point of the flat-during-backwardation gate is to survive stress
periods, but the full-sample MDD shows the gate reacts too slowly/coarsely
to avoid the Volmageddon-style single-day/multi-day gap risk in this
repo's daily-bar backtest).

## Decision: REJECTED

Both Sharpe and max-drawdown validators fail decisively on the full
sample. This directly corroborates the source article's own disclosed
42% max drawdown (Volmageddon) — which already exceeds this repo's 0.25
MDD budget before any transaction-cost/walk-forward analysis — and its own
recommendation that a raw application of the trade must be scaled down to
35-40% of portfolio to survive, which is an allocation-sizing overlay outside
this repo's single-instrument long/flat backtest scope.

## Notes for future iterations

- This is the first strategy in this repo's now 70+ VIX/term-structure
  entries to trade the actual volatility ETF product (SVXY) directly rather
  than using VIX/VIX3M as a side-gate on QQQ/SPY/BTC/ETH price action.
- A future iteration could revisit with a stricter/faster stress-detection
  trigger (e.g. VIX daily % change as an immediate kill-switch rather than
  relying on the VIX/VIX3M ratio crossing 1.0, which lagged the Volmageddon
  spike) — but note this repo's per-strategy backtest doesn't support the
  source's own suggested fix (35-40% portfolio-level position sizing), so
  any fix must reduce full-instrument MDD directly via faster signal
  reaction, not just position-sizing.
