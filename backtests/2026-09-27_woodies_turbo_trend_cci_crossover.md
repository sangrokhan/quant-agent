# Backtest Report: Woodie's Turbo/Trend CCI Dual-Line Crossover

**Strategy file:** `strategies/2026-09-27_woodies_turbo_trend_cci_crossover.py`
**Date:** 2026-09-27
**Hypothesis ID:** see `knowledge_base/strategies_log.jsonl`

## Hypothesis

Woodie's CCI trading system (Ken Wood) explicitly separates a fast "Turbo
CCI" (period 6) from a slower "Trend CCI" (period 14 for sub-60-minute bars,
20 for higher timeframes), per
https://ftmo.com/en/blog/woodies-cci-system/ (visited this iteration).
Long entry: Turbo CCI crosses above Trend CCI while Trend CCI has been
positive for at least `trend_established_bars` consecutive bars (source's
own "six lines above the Zero-Line" uptrend definition). Exit: Turbo CCI
crosses back below Trend CCI, Trend CCI itself drops below zero, or a
max-hold time-stop.

Distinct from this repo's 5 prior Woodie's CCI entries (Zero-Line-Reject,
Trend-Line-Break, Hook-From-Extreme, Woodie Pivot Points, Pivot Point
continuous-sizing dial) -- none of those used this dual-line
fast/slow-CCI-crossover mechanism.

## Step 6 grid summary

`param_grid`: turbo_period in {4,6,9}, trend_period in {14,20},
trend_established_bars in {4,6,8}, max_hold_days in {15,20,30}
`symbols`: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
`vol_regime_splits`: 3 (low/mid/high realized-vol terciles)

- total_cells: 648, passed_cells: 141, **pass_fraction: 0.218**
- by_asset_class: equity 93/324 (0.287), crypto 48/324 (0.148)
- by_vol_regime: low 96/216 (0.444), mid 27/216 (0.125), high 18/216 (0.083)
- best_cell: turbo_period=4, trend_period=20, trend_established_bars=4,
  max_hold_days=15, SPY, low-vol regime, Sharpe 2.55
- worst_cell: turbo_period=9, trend_period=14, trend_established_bars=6,
  max_hold_days=15, SPY, mid-vol regime, Sharpe -1.37

Edge is concentrated almost entirely in the low-vol tercile (44% pass) and
collapses in mid/high-vol regimes (12.5%/8.3% pass) -- consistent with a
whipsaw-prone fast-vs-slow-oscillator crossover in choppier conditions.

## Step 7 single-config validation (best full-sample QQQ config)

Config: turbo_period=9, trend_period=20, trend_established_bars=4,
max_hold_days=20 (best average full-sample Sharpe across QQQ terciles from
the grid).

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.868 FAIL | 0.321 FAIL |
| Max Drawdown (<=0.25) | 0.068 PASS | 0.044 PASS |
| TC-survival net Sharpe (>=0.5) | 0.147 FAIL | -0.236 FAIL |
| Walk-forward (>=0.75 pass frac) | 1.0 PASS | 0.5 FAIL |
| Parameter sensitivity (rel std <=0.5) | 0.551 FAIL | 0.987 FAIL |

QQQ: 170 trades, SPY: 160 trades over 2018-2026 -- high turnover (fast CCI
crossover fires frequently), which is the direct cause of the TC-survival
failure (drag ~0.17/0.16 vs a full-sample-normalized annual net Sharpe under
threshold).

## Decision: REJECT (decisive)

Fails 3/5 validators on both QQQ and SPY (Sharpe, TC-survival, parameter
sensitivity), with SPY additionally failing walk-forward. MDD is very
healthy (well within limits) but the strategy trades too often relative to
its edge to survive realistic transaction costs, and the underlying edge is
regime-narrow (low-vol only) and parameter-fragile.

Crypto not separately validated given equity already fails decisively and
the grid's crypto pass_fraction (0.148) was even weaker than equity's.

## Possible future rescue angle (not pursued this iteration)

A min_hold_days hysteresis gate (suppress the turbo/trend cross-back exit
for N bars after entry, matching this repo's established rescue pattern
used for Klinger/ZLEMA/Bulkowski-Weinstein) could reduce turnover and might
rescue TC-survival, but the underlying Sharpe near-miss and severe
parameter sensitivity (rel_std 0.55-0.99) suggest the base signal itself is
weak, not just cost-starved -- a future iteration could attempt this fix but
should not expect a large improvement.
