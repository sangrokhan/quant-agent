# ADX/DMI Directional Crossover + ADX-Rising-Slope Confirmation

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-11_adx_dmi_rising_slope_confirm.py`
**KB id:** 2026-09-11-097

## Hypothesis

Source: https://quantstock.org/blog/adx-indicator-trading-strategy (visited this
iteration). Source's disclosed "Bullish Setup" rule: wait for +DI to cross above
-DI, confirm ADX above 20 (preferably 25), AND "enter long when ADX is rising,
confirming the uptrend is strengthening" — an explicit slope condition layered on
top of a static level gate.

This is a direct, source-grounded fix attempt for the earlier rejected strategy
2026-09-03-017 (static `ADX > threshold` gate), whose specific rejection reason
was catastrophic parameter sensitivity to the exact threshold chosen (rel std
0.53, Sharpe decaying monotonically from 0.96 at threshold=15 to 0.17 at
threshold=30 on QQQ). Hypothesis: replacing the sensitive absolute-level cutoff
with a relative ADX-rising-slope condition (`ADX(t) > ADX(t - lookback)`), plus a
much looser static floor purely to exclude dead/near-zero ADX, should be far less
sensitive to the exact parameter chosen.

## Grid test (validation/grid_test.py::run_strategy_grid)

param_grid = `{adx_floor: [10, 15, 20], adx_slope_lookback: [3, 5, 8]}`,
symbols = QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto), vol_regime_splits=3,
2018-01-01 to 2026-09-01. 108 cells total.

- **pass_fraction: 0.148** (16/108)
- by_asset_class: equity 16/54, crypto 0/54
- by_vol_regime: low 16/36, mid 0/36, high 0/36
- best cell: adx_floor=10, adx_slope_lookback=8, QQQ, low-vol, Sharpe 1.66
- worst cell: adx_floor=20, adx_slope_lookback=3, SPY, mid-vol, Sharpe -1.45

Same equity-only, low-vol-concentrated pattern seen across nearly every trend
strategy in this repo.

## Single-config validators (best grid config: adx_floor=10, adx_slope_lookback=8, period=14, max_hold_days=40)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.493 FAIL | 0.375 FAIL |
| Max Drawdown (<=0.25) | 0.127 PASS | 0.089 PASS |
| TC survival (net Sharpe >=0.5) | 0.279 FAIL | 0.089 FAIL |
| Walk-forward (>=0.75 splits positive) | 0.75 (3/4) PASS | 0.75 (3/4) PASS |
| Parameter sensitivity (rel std <=0.5) | **0.383 PASS** | 31.37 FAIL (mean near zero) |

## Outcome: REJECTED

Full-sample Sharpe and transaction-cost survival both fail on QQQ and SPY —
the grid's headline 1.66 Sharpe best-cell is a narrow low-vol-tercile artifact,
not representative of the full-sample edge, consistent with the pattern
documented across most of this repo's trend-following strategies.

**However, the specific hypothesis under test (does an ADX-slope condition
reduce parameter sensitivity vs. a static threshold?) is partially confirmed**:
QQQ's parameter-sensitivity rel-std improved from 0.53 (FAIL, 2026-09-03-017
static-threshold version) to 0.383 (PASS) under the slope-based gate — a
real, if modest, robustness improvement. SPY's param-sensitivity comparison is
not meaningful here since its mean Sharpe across the grid is close to zero
(-0.008), making the relative-std ratio numerically unstable/inflated rather
than reflecting genuine fragility.

Crypto (BTC/ETH) rejected decisively, 0/54 grid cells — consistent with every
other trend/momentum strategy tested on crypto in this repo to date.

## Notes for future iterations

The ADX/DMI directional-crossover *entry trigger* itself appears to be the
weak link (rejected across three separate confirmation-filter designs now:
plain static threshold -017, and this slope-confirmed variant), not the
strength-gate mechanism layered on top of it. A future loop revisiting DMI/ADX
should consider replacing the DI-crossover trigger itself (too frequent/noisy)
rather than iterating further on the ADX confirmation filter.
