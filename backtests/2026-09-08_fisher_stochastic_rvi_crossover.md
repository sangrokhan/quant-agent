# Ehlers Fisher Stochastic RVI Crossover — Backtest Report

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_fisher_stochastic_rvi_crossover.py`
**Knowledge base id:** 2026-09-08-029

## Hypothesis

Per John Ehlers' "Cybernetic Analysis for Stocks and Futures" (pgs 101-104),
summarized via [FMZ's strategy writeup](https://www.fmz.com/lang/en/strategy/436218)
and [TradingView's "Ehlers Fisher Stochastic Relative Vigor Index [CC]"](https://www.tradingview.com/script/vGWGjnc4-Ehlers-Fisher-Stochastic-Relative-Vigor-Index-CC/)
indicator page: Ehlers' Relative Vigor Index (RVI) is stochastic-normalized
over a rolling window (rescaled -1..+1 within its own rolling
high/low, per the generic Ehlers Fisher-of-stochastic Pine pattern found
via search), then a Fisher Transform is applied to sharpen turning points.
Long entry on Fisher crossing above its 1-bar-lagged Trigger; exit on
cross-down or a `max_hold_days` time-stop.

Distinct from existing repo strategies: plain RVI-crossover strategies
(2026-09-04-061/130/147) cross raw SMA-smoothed RVI vs its SMA signal line;
Fisher-of-price strategies (2026-09-04-051, 2026-09-05-086) apply the
Fisher transform directly to price. This strategy applies Fisher to a
stochastic-normalized RVI — a bounded oscillator-of-an-oscillator input.

## Single-config validators (QQQ, full sample 2015-01-01 to 2026-09-01)

Best grid config: `rvi_length=14, stoch_length=14, fisher_smooth=5, max_hold_days=15`

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ PASS | 1.091 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 21.9% | ≤ 25% |
| Transaction cost survival (10bps/trade, 422 trades) | ✅ PASS | net Sharpe 0.593 | ≥ 0.5 |
| Walk-forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` broken in this install) | ✅ PASS | 4/4 splits positive Sharpe | ≥ 75% |
| Parameter sensitivity (8-cell QQQ-only sweep, relative std) | ✅ PASS | 0.444 | ≤ 0.5 |

**All 5 validators pass → ACCEPT (equity/QQQ scope).**

## Grid test summary (96 cells: rvi_length∈{10,14} × stoch_length∈{14,20} × fisher_smooth∈{3,5} × 2 equity symbols × 2 crypto symbols × 3 vol regimes)

- `pass_fraction`: 22.9% (22/96)
- `by_asset_class`: equity 22/48 passed; **crypto 0/48 (decisive reject)**
- `by_vol_regime`: low 12/32, mid 10/32, **high 0/32 (decisive reject in high-vol regime)**
- `best_cell`: rvi_length=14, stoch_length=14, fisher_smooth=5 — equity/QQQ/mid-vol, Sharpe 2.026
- `worst_cell`: rvi_length=10, stoch_length=20, fisher_smooth=5 — equity/SPY/mid-vol, Sharpe -0.457

## Scope / honest limitations

- Edge is concentrated in **equity, low/mid volatility regimes**. Zero
  passing cells in high-vol regime or on any crypto symbol — do not deploy
  outside equity/low-mid-vol scope.
- QQQ outperforms SPY in the grid; SPY was not separately validated with
  the single-config validator suite this iteration (future iteration could
  check whether SPY passes at its own best params).
- Walk-forward uses the repo's standard manual 4-equal-slice fallback
  (known `vectorbt` API gap, documented since 2026-09-03-002).

## Sources

- https://www.fmz.com/lang/en/strategy/436218
- https://www.tradingview.com/script/vGWGjnc4-Ehlers-Fisher-Stochastic-Relative-Vigor-Index-CC/
- https://kr.tradingview.com/script/rzz2xJAo-Ehlers-Fisher-Stochastic-Relative-Vigor-Index-Strategy/ (attribution confirmation only)
- Google SERP snippet confirming generic Fisher-of-stochastic normalization formula (value1 = 2*(src-lowestLow)/(highestHigh-lowestLow)-1, clamped, EMA-smoothed, then Fisher log transform)
