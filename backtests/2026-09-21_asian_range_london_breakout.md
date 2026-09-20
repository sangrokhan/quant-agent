# Asian-Range London-Session Breakout (Crypto Hourly) — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_asian_range_london_breakout.py`
**Outcome:** REJECTED

## Hypothesis

Per QuantifiedStrategies.com's "London Breakout Strategy" (freely available,
https://www.quantifiedstrategies.com/london-breakout-strategy/), the Asian
trading session establishes a support/resistance range; a breakout above
that range during the London session signals likely continuation. Adapted
to this repo's 24h crypto markets (BTC/USDT, ETH/USDT) using hourly OHLCV.
0 prior session-based (Asian/London/first-hour-range) entries in this
repo. Not applicable to equity (only daily-bar data available via
`load_equity`) -- `generate_signals` returns all-flat on daily bars, same
documented pattern as the existing session-split strategy
(2026-09-11_crypto_session_split_momentum_reversal.py).

## Grid test (Step 6, manual -- `grid_test.py`'s `run_strategy_grid`
force-loads daily bars for every symbol, incompatible with this
fundamentally hourly-bar strategy, so a manual hourly-bar grid was run
directly against `load_crypto`'s native `interval="1h"` data)

`param_grid={"asian_end_hour": [6,8], "breakout_pct": [0.0,0.002,0.005],
"max_hold_bars": [4,8]}`, symbols `["BTC/USDT","ETH/USDT"]`,
2019-01-01 to 2026-09-01, full-sample Sharpe per cell (vol-regime tercile
slices were too sparse in trade count to compute a stable per-regime
Sharpe on this signal's turnover, so only full-sample is reported).

- **pass_fraction (full-sample Sharpe≥1.0): 0.083** (2/24 cells)
- **by_symbol:** BTC/USDT 0/12 passed; ETH/USDT 2/12 passed
- **best_cell:** ETH/USDT, `asian_end_hour=6, breakout_pct=0.002,
  max_hold_bars=4`, full-sample Sharpe 1.064
- ETH/USDT Sharpes cluster tightly (0.73-1.06) across all 12 param combos
  — reasonably parameter-stable, but BTC/USDT tops out at 0.98 and never
  clears the threshold decisively.

## Single-config validation (ETH/USDT, best config)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.217 (validators.py's `check_sharpe_ratio` hardcodes `freq="D"` internally regardless of the `periods_per_year` arg passed -- a pre-existing bug in the shared validator when applied to hourly bars; a manual `vbt.returns(freq="H").sharpe_ratio()` calc gave 1.064, matching the grid) | ≥1.0 | fails under the buggy annualization, but the bug affects only this one metric |
| Max drawdown | **0.554** | ≤0.25 | **FAIL (decisive, more than double the budget)** |
| Transaction cost survival (5bps/trade, 3074 trades over 7.5yr) | net Sharpe 0.018 | ≥0.5 | **FAIL (decisive -- extreme turnover)** |
| Walk-forward (4 contiguous splits) | 0.75 (3/4 positive) | ≥0.75 | pass |
| Parameter sensitivity (breakout_pct sweep) | relative_std 0.068 | ≤0.5 | pass |

## Decision

**Rejected.** Regardless of the Sharpe annualization discrepancy noted
above (a validators.py limitation for hourly-bar strategies, worth fixing
in a future loop), the max drawdown (0.554, more than double the 0.25
budget) and transaction-cost survival (net Sharpe collapses to 0.018 at a
realistic 5bps/trade given ~3074 trades over the sample) are both
decisive, unambiguous failures independent of that bug. The Asian-range
breakout signal fires far too often (short max_hold_bars, tight
breakout_pct) to survive realistic trading costs, and drawdowns are severe
during the sample's crypto bear markets. Consistent with the source's own
stated skepticism about the raw London Breakout rule without added risk
management/filters.
