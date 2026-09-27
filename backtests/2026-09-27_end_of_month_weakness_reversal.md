# Backtest Report: End-of-Month Calendar-Day Weakness Reversal

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_end_of_month_weakness_reversal.py`
**Hypothesis id:** 2026-09-27-047

## Hypothesis

Per QuantifiedStrategies.com's "End of Month Trading Strategy 2026-
S&P500 Outperformance!"
(https://www.quantifiedstrategies.com/end-of-month-trading-strategy/,
read via `browser_exec` — `web_search` returned only snippet-level
results, browser used to read the full disclosed rule directly): enter
long at the close on any CALENDAR day 29, 30, or 31 of the month (not
trading-day count) whose own close was negative; exit at the close on the
first bar where two consecutive closes are each higher than the prior
close, or when cumulative return since entry hits a profit target
(source's own worked example: 1% on SPY), whichever comes first. No
stop-loss in the source; this repo's convention adds a `max_hold_days`
safety valve. Distinct from this repo's many other turn-of-month entries
(all fixed calendar WINDOWS regardless of that day's direction) via the
explicit conditional weakness trigger + adaptive exit.

## Grid test summary (Step 6)

`param_grid={"profit_target": [0.005, 0.01, 0.015], "max_hold_days": [10,
15, 20]}`, symbols equity=[QQQ, SPY] crypto=[BTC/USDT, ETH/USDT],
`vol_regime_splits=3`, sample 2019-01-01 to 2026-09-01.

- **total_cells:** 108, **passed_cells:** 29, **pass_fraction:** 0.269
- **by_asset_class:** equity 27/54 (0.50), crypto 2/54 (0.04 — mostly
  decisive crypto reject, 2 marginal passes)
- **by_vol_regime:** low 0/36 (0.0), mid 9/36 (0.25), high 20/36 (0.56) —
  edge concentrated in mid/high-vol regimes, opposite of most other
  strategies in this repo (makes economic sense: the entry trigger is
  conditioned on a negative move, which is naturally rarer/less
  meaningful in low-vol/quiet regimes).
- **best_cell:** SPY, high-vol, `profit_target=0.015/max_hold_days=10`,
  Sharpe 1.72
- **worst_cell:** ETH/USDT, low-vol, `profit_target=0.01/max_hold_days=20`,
  Sharpe -0.78

## Single-config validation (Step 7) — profit_target=0.01/max_hold_days=15, full sample

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | FAIL 0.816 | **PASS** 1.277 |
| Max drawdown (<=0.25) | PASS 0.114 | PASS 0.059 |
| Transaction-cost survival (net Sharpe >=0.5, 10bps/trade) | PASS 0.688 (54 trades) | **PASS** 1.056 (56 trades) |
| Walk-forward (manual 4-split substitute, pass_fraction>=0.75) | PASS 1.0 (4/4 splits positive) | **PASS** 1.0 (4/4 splits positive) |
| Parameter sensitivity (relative_std<=0.5, 25-cell local grid) | PASS 0.049 | PASS 0.122 |

SPY: **all 5 validators pass**. QQQ fails only on Sharpe (0.816 < 1.0) —
a quick per-symbol retune (`profit_target` in {0.005..0.02} x
`max_hold_days` in {8..25}, 42 combos) found QQQ's best achievable Sharpe
is 0.886 at `profit_target=0.0075/max_hold_days=10`, still short of the
1.0 threshold, so this near-miss was not pursued further this iteration
(the gap is small enough to be a candidate for a future sub-iteration
rescue, e.g. with an added trend filter, but not close enough to accept
outright). Crypto (BTC/USDT, ETH/USDT) mostly decisively rejected across
the grid (2/54 marginal passes only), consistent with this being an
equity-calendar-seasonality effect without an economic mechanism in
24/7 crypto markets.

## Decision

**Accepted for SPY only** (`profit_target=0.01, max_hold_days=15`). QQQ
rejected as a near-miss (Sharpe 0.816, best achievable via retune 0.886)
and crypto rejected (feasibility/economic-mechanism mismatch, mostly
decisive fails).
