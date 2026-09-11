# Ehlers Roofing Filter Signal-Line Cross + 200 EMA Trend Gate

**Hypothesis:** Ehlers' Roofing Filter is a two-stage DSP: 2-pole high-pass
(strips slow trend/drift) then SuperSmoother low-pass (strips fast noise),
producing a line that "hugs price action closely but with far less
jitter than a typical moving average." Per
https://theindicatorlab.com/reviews/ehlers-roofing-filter/ (via
browser_exec/google.com fallback): "Long Entry: Wait for the Roofing
Filter line to cross above its 3-period SMA, and price should be above
the 200 EMA on the same timeframe... Exit: Trail with the filter line
itself." Operationalized as RF-crosses-its-own-3-period-SMA-signal-line,
gated by close>EMA(200), exit on the reverse signal cross or a
max_hold_days time-stop.

Source: https://theindicatorlab.com/reviews/ehlers-roofing-filter/ (via
browser_exec fallback; web_search DDGS backend TLS/connection errors this
iteration).

## Step 6 Grid Test Summary (72 cells: 2 hp_period x 3 lp_period x 1
trend_window x 4 symbols x 3 vol regimes)

- pass_fraction: 0.139 (10/72)
- by_asset_class: equity 10/36 passed, crypto 0/36 (decisively rejected)
- by_vol_regime: low 9/24, mid 1/24, high 0/24 (edge almost entirely
  low-vol)
- best_cell: hp_period=48, lp_period=10, trend_window=200, SPY, low-vol
  regime, Sharpe=1.90

## Step 7 Single-Config Validation (best config: hp_period=48,
lp_period=10, trend_window=200, full sample 2019-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|--------|--------|-----|-------------|---------------|---------------------|
| QQQ | 0.348 (FAIL) | 0.197 (PASS) | 0.130 (FAIL, thr 0.5) | 0.75 (PASS) | 0.179 rel std (PASS) |
| SPY | 0.518 (FAIL) | 0.234 (PASS) | 0.196 (FAIL, thr 0.5) | 1.00 (PASS) | 0.181 rel std (PASS) |

## Decision: REJECTED

Both QQQ and SPY fail full-sample Sharpe (0.35, 0.52, both well below
1.0) and transaction-cost survival (0.13, 0.20, both well below 0.5) at
the grid-best config. Root cause: the signal-line-cross entry fires very
frequently (150+ trades over 7 years, roughly 22/year) since the
high-pass-then-low-pass filter is a fast oscillator that crosses its own
short SMA often even inside a stable uptrend -- the grid's apparent
low-vol-tercile edge (9/24) does not survive full-sample costs. Crypto
decisively rejected 0/36. Not accepted; a slower signal_period or a
minimum-holding-period filter could reduce trade frequency in a future
revisit, but this is a clean rejection given the magnitude of both
failures.
