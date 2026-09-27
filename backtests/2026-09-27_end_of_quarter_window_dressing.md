# Backtest Report: End-of-Quarter Window Dressing

**Strategy file:** `strategies/2026-09-27_end_of_quarter_window_dressing.py`
**Date:** 2026-09-27
**Source:** QuantifiedStrategies.com, "End of Quarter Effect (Strategy) in
the Stock Market: Backtest and Performance Analysis"
(https://www.quantifiedstrategies.com/end-of-quarter-effect-strategy/,
read via browser_exec this iteration -- web_search DDGS backend returned
"No results found" on the direct query).

## Hypothesis

Source's own disclosed rule: go long on the 6th-to-last trading day of each
calendar quarter (i.e. hold the final 5 trading days of the quarter), exit
at the quarter's close. Source's own backtest (S&P 500 cash index since
1960, excluding dividends) finds this unconditional (all-4-quarters)
construction weak/unpromising overall, and NEGATIVE if Q4 (Santa Claus
Rally window) is excluded. Tested here on both equity and crypto per this
repo's grid convention.

## Single-config metrics (SPY, quarter_window=5, source's disclosed base case)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.490 | >= 1.0 | **FAIL** |
| Max drawdown | 0.082 | <= 0.25 | pass |
| Transaction cost survival | not run (decisive Sharpe fail) | - | skipped |
| Walk-forward | not run (decisive Sharpe fail) | - | skipped |
| Parameter sensitivity | see grid below | - | see grid |

Corroborates the source's own finding: on SPY 2015-2026, the unconditional
5-trading-day quarter-end window produces a positive but weak Sharpe well
below the 1.0 acceptance bar, consistent with the source's own conclusion
that "the end of quarter effect in the stock market is a myth" once you
look past the Q4/Santa-Claus-driven portion.

## Grid summary (Step 6)

- Param grid: `quarter_window` in {3, 5, 7}
- Symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits=3
- Total cells: 36; **passed: 2 (pass_fraction 0.056)**
- By asset class: equity 0/18 (decisive fail on the source's own target
  asset class), crypto 2/18 (only BTC/USDT low-vol regime passes, at
  quarter_window=3, Sharpe 1.066 -- a narrow, likely spurious pass given
  only 3 vol-regime x 3 param x 2 symbol = 18 crypto cells).
- By vol regime: low 2/12, mid 0/12, high 0/12.
- Best cell: crypto BTC/USDT, quarter_window=3, low-vol, Sharpe 1.066.
- Worst cell: equity QQQ, quarter_window=7, mid-vol, Sharpe -0.743.

## Decision: REJECT

Decisive fail on equity (the source's own stated target asset, 0/18 grid
cells, Sharpe 0.34-0.49 across all three quarter_window values, all below
the 1.0 threshold). The lone crypto pass (2/36 overall, pass_fraction 0.056)
is too narrow a slice (single symbol, single vol regime, single param
value) to support acceptance and is not the asset class the source's own
hypothesis targets. Strategy file kept in `strategies/` as a record of a
rejected attempt.
