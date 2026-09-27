# Backtest Report: Bulkowski Broadening Top/Bottom "Buy at 3rd Touch" Reversal

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_broadening_top_bottom_reversal.py`
**Knowledge base id:** 2026-09-27-124

## Hypothesis

Per Thomas Bulkowski's ThePatternSite.com "Broadening Tops" page
(https://www.thepatternsite.com/bt.html, read via browser_exec this
iteration), a broadening/megaphone formation (upper trendline sloping up,
lower trendline sloping down, price range widening, at least 3 touches per
side) admits a disclosed "buy at 3rd touch" tactic: buy when price touches
the lower (ascending-range) trendline for the third time and begins rising
(explicitly flagged by the source itself as "a high risk entry"), mirrored
by a "short at the top" tactic at the upper trendline.

This is the first "broadening"/"megaphone" pattern strategy tested in this
repo (0 prior hits in strategies_index.jsonl for "broadening", "diamond
pattern", "megaphone").

## Implementation

- Rolling `pivot_window`-bar swing-high/low detection (confirmed with a
  `pivot_window`-bar lag to avoid look-ahead).
- Over a trailing `lookback` window, OLS-fit trendlines to the confirmed
  pivot highs and pivot lows separately.
- "Broadening regime" = upper trendline slope > 0 AND lower trendline
  slope < 0 (megaphone shape).
- Long entry: in a broadening regime, close is within `touch_tolerance` of
  the projected lower trendline value, the last bar-over-bar return just
  turned positive, and at least `min_touches` confirmed pivot lows feed the
  trendline.
- Exit: close reaches the projected upper trendline (mirror of "short at
  the top", used as a long-only take-profit), OR the broadening regime
  breaks down, OR `max_hold_days` time-stop.

## Grid test (validation/grid_test.py::run_strategy_grid)

Grid: `touch_tolerance` in {0.01, 0.015, 0.02} x `min_touches` in {3, 4} x
`max_hold_days` in {15, 25}, symbols equity={QQQ, SPY} crypto={BTC/USDT,
ETH/USDT}, `vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- total_cells = 144, passed_cells = 8, **pass_fraction = 0.0556**
- by_asset_class: equity 8/72, crypto 0/72 (crypto decisively rejected)
- by_vol_regime: low 0/48, mid 8/48, high 0/48 (edge, if any, confined
  entirely to the mid-vol tercile)
- best_cell: QQQ, touch_tolerance=0.02, min_touches=3, max_hold_days=15,
  mid-vol regime, Sharpe 1.256
- worst_cell: BTC/USDT, touch_tolerance=0.01, min_touches=3,
  max_hold_days=15, low-vol regime, Sharpe -1.427

## Single-config validation (best grid config: touch_tolerance=0.02,
min_touches=3, max_hold_days=15)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **FAIL** 0.521 | **FAIL** 0.333 |
| Max drawdown (<=0.25) | pass 0.075 | pass 0.075 |
| Transaction-cost survival (net Sharpe >=0.5) | **FAIL** 0.396 | **FAIL** 0.188 |
| Walk-forward | tooling error (vectorbt.utils.splitting API unavailable in this env) | same |
| Parameter sensitivity (rel std <=0.5) | pass 0.173 | **FAIL** 1.566 |

Trade counts: QQQ 25 trades, SPY 22 trades over the full sample (2018-2026)
-- sparse signal, consistent with the source's own "high risk entry"
framing and the narrow mid-vol-only grid pass pattern.

## Decision: REJECTED

Full-sample Sharpe fails decisively on both QQQ and SPY (well under the 1.0
threshold), transaction-cost survival also fails on both, and SPY's
parameter sensitivity is highly unstable (relative std 1.57, driven by the
strategy going net negative at several nearby parameter combinations).
Crypto is a decisive 0/72 grid reject. The grid's isolated mid-vol-only
edge (8/48 cells) does not generalize to the full sample or survive
transaction costs. Consistent with Bulkowski's own explicit "high risk
entry" caveat for this specific tactic.

Strategy file and this report are kept in the repo as a record of a
rejected attempt (per RESEARCH_LOOP.md Step 8) -- not live/in-use.
