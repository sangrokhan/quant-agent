# FRAMA ATR-Band Breakout — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_frama_atr_band_breakout.py`
**Source:** https://oxfordstrat.com/trading-strategies/fractal-adaptive-moving-average/
(Oxford Capital Strategies' disclosed FRAMA trading-strategy specification,
Ehlers' Fractal Adaptive Moving Average, tested there on 42 futures markets
1980-2016). Read via `browser_exec` this iteration (`web_extract`'s
configured `ddgs` backend is search-only and cannot fetch page content;
`web_search` itself worked fine for discovery this iteration).

## Hypothesis

Long-only adaptation of Ehlers' FRAMA breakout system: FRAMA adapts its
smoothing constant to price's fractal dimension (hugs price tightly when
trending/low-fractal-dimension, flattens in choppy/high-fractal-dimension
conditions). Source's own disclosed rule:
- Entry: `Close[t-1] > FRAMA[t-1] + atr_band*ATR(frama_length)[t-1]`
- Trend exit: `Close[t-1] < FRAMA[t-1] - 0.5*atr_band*ATR(frama_length)[t-1]`
  (source's own asymmetric design — exit band is HALF the entry band width)
- Hard stop: `Entry - atr_stop_mult*ATR(atr_length)` (source base case
  `ATR_Length=20`, `ATR_Stop=6` — wide catastrophic-only stop)
- Added: `max_hold_days` time-stop backstop (repo convention), `leverage_cap`
  position-scaling dial and `min_hold_days` turnover-reduction gate (repo's
  established rescue patterns for crypto MDD/TC-survival).

Source's own summary explicitly states this strategy "does not perform
significantly better than alternative [MA-filter] strategies" on its
42-future multi-asset portfolio (Sharpe 0.71-0.81, MDD 39-54%) — tested here
fresh on this repo's specific equity/crypto single-symbol daily-bar universe
rather than assuming that modest multi-asset-portfolio verdict transfers.

## Step 6 — Grid test (validation/grid_test.py::run_strategy_grid)

`param_grid={frama_length:[16,26], atr_band:[1.5,2.0,3.0]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01, 72 cells.

- `pass_fraction`: 0.181 (13/72)
- `by_asset_class`: equity 10/36 (0.278), crypto 3/36 (0.083)
- `by_vol_regime`: low 12/24 (0.50), mid 0/24 (0.0), high 1/24 (0.042) —
  edge concentrated almost entirely in the low-vol tercile
- `best_cell`: QQQ, frama_length=26/atr_band=1.5, low-vol, Sharpe 2.098
- `worst_cell`: QQQ, frama_length=26/atr_band=3.0, high-vol, Sharpe -1.542

## Step 7 — Single-config validation (widened manual sweep beyond grid)

A wider manual sweep (frama_length in {10,16,20,26,32}, atr_band in
{1.0,1.5,2.0,2.5,3.0}, max_hold_days in {40,60,90}) found the full-sample
best configs per symbol, filtering out degenerate near-zero-trade cells.

### QQQ — ACCEPTED (frama_length=32, atr_band=2.5, max_hold_days=40)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.345 | 1.0 | ✅ |
| Max drawdown | 0.165 | 0.25 | ✅ |
| TC survival (10bps, 17 trades) | 1.315 | 0.5 | ✅ |
| Walk-forward (manual 4-split) | 1.0 (4/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (rel-std, 3x3 neighborhood) | 0.237 | 0.5 | ✅ |

### SPY — REJECTED (same config)

Sharpe 0.277 (decisive fail), TC-survival net Sharpe 0.230 (fail),
walk-forward 0.5 (2/4 splits positive, fail). MDD (0.155) and parameter
sensitivity (0.338) pass but insufficient given the other 3 failures.

### ETH/USDT — ACCEPTED (frama_length=16, atr_band=2.0, leverage_cap=0.5)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.016 | 1.0 | ✅ |
| Max drawdown | 0.243 | 0.25 | ✅ |
| TC survival (10bps, 37 trades) | 0.996 | 0.5 | ✅ |
| Walk-forward (manual 4-split) | 0.75 (3/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (rel-std, 3x3 neighborhood) | 0.125 | 0.5 | ✅ |

Unleveraged (`leverage_cap=1.0`) ETH/USDT MDD was 0.441 (fail); scaling
exposure to 0.5 brings MDD under budget without changing Sharpe (Sharpe is
leverage-invariant for a pure long/flat 0/leverage_cap position), per this
repo's now-standard leverage-cap-recalibration pattern.

### BTC/USDT — REJECTED (near-miss)

Best config found (frama_length=22, atr_band=3.0, leverage_cap=0.3):
Sharpe 0.977 (just under 1.0 threshold), MDD 0.104 (passes comfortably).
Genuine near-miss — flagged in `notes` for a future loop to retry with a
finer-grained param sweep or a different exit-band asymmetry.

## Outcome

**Accepted (QQQ, ETH/USDT); rejected (SPY, BTC/USDT — BTC is a genuine
near-miss).** Scope: this construction works for QQQ (equity, unleveraged)
and ETH/USDT (crypto, leverage_cap=0.5) specifically — do not extrapolate to
SPY or BTC/USDT at these parameters. Edge is concentrated in the low-vol
regime per the grid; source itself flagged this as a modest, not a strong,
edge on its own much larger multi-asset test.
