# Cup with Handle Breakout — 2026-09-28

**Hypothesis:** Bulkowski Cup with Handle chart pattern (source rank #3 of
39, average rise 54%, break-even failure rate 5%). Extends this repo's
already-accepted bowl-detection framework (Rounding Bottom, 2026-09-24-101
/102) with a distinct right-rim confirmation, a handle-consolidation phase
(upper half of cup, short-handle bias per source's own trading tip), and
the source's own Measure Rule target (61% of cup height).

**Source:** https://thepatternsite.com/cup.html (read via `browser_exec`
after `web_search`'s DDGS backend returned no results for two related
queries this iteration).

## Grid test (validation/grid_test.py::run_strategy_grid)

144 cells: `cup_window` in [40, 60, 90] x `handle_max_days` in [15, 22] x
`target_pct` in [0.5, 0.61], equity [QQQ, SPY] + crypto [BTC/USDT,
ETH/USDT], `vol_regime_splits=3`.

- **pass_fraction: 0.292** (42/144)
- by_asset_class: equity 28/72, crypto 14/72 (both non-trivial, unusual
  for this repo's typical equity-favored pattern-breakout family)
- by_vol_regime: low 27/48, mid 3/48, high 12/48

## Single-config validators (full sample 2019-01-01 to 2026-09-01)

### QQQ (cup_window=40, handle_max_days=15, target_pct=0.5)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.019 | 1.0 |
| Max drawdown | PASS | 0.104 | 0.25 |
| Transaction cost survival | PASS | 0.844 net Sharpe | 0.5 |
| Walk-forward (4 splits) | PASS | 0.75 (3/4 positive) | 0.75 |

**Decision: ACCEPTED (QQQ)** — all 4 runnable validators pass, 61 trades
over 7.5yr, modest cost drag.

### BTC/USDT (cup_window=60, handle_max_days=15, target_pct=0.5)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.073 | 1.0 |
| Max drawdown | PASS (barely) | 0.248 | 0.25 |
| Transaction cost survival | PASS | 1.033 net Sharpe | 0.5 |
| Walk-forward (4 splits) | **FAIL** | 0.5 (2/4 positive) | 0.75 |

**Decision: REJECTED (BTC/USDT)** — walk-forward fails despite strong
full-sample Sharpe/TC-survival; the edge is not consistently present
across out-of-sample sub-periods, and MDD only barely clears the 0.25 cap.

SPY and ETH/USDT were not run through full single-config validators this
iteration (best full-sample Sharpe from the parameter scan was 0.85 and
0.89 respectively — both below the 1.0 threshold, so not worth the
validator budget this iteration; flagged as near-misses for a future
per-symbol retune).

## Notes for future loops

- QQQ config accepted; strategy file kept live in `strategies/`.
- BTC/USDT is a near-miss (Sharpe/MDD/TC all pass, only walk-forward
  fails) — worth revisiting with a narrower parameter search focused on
  walk-forward stability specifically.
- SPY (Sharpe 0.85) and ETH/USDT (Sharpe 0.89) are near-misses worth a
  per-symbol retune in a future iteration.
