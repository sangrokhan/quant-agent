# Backtest report: Wyckoff Spring accumulation-range failed-breakdown reversal

**Strategy file:** `strategies/2026-09-09_wyckoff_spring_range_reversal.py`
**Knowledge base id:** 2026-09-09-105
**Outcome:** REJECTED

## Hypothesis

Per sdk-trading.com's definition (Dennis York): "A Wyckoff spring is a
failed downside probe below the lower boundary of a trading range. The
move becomes meaningful only if price returns into the prior range instead
of accepting lower prices below support." Operationalized as: a rolling
`range_window`-day range defines support/resistance; a probe below range
low that reclaims (close back above range low) within `confirm_bars`
triggers a long entry; exit at close above range high (target), close
below the probe low (stop), or `max_hold_days` time-stop.

## Grid test summary (Step 6)

- Grid: `range_window` in [10, 20, 30] x `confirm_bars` in [1, 3] x
  `max_hold_days` in [15, 25] x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol
  terciles = 144 cells.
- `pass_fraction`: **0.049** (7/144)
- `by_asset_class`: equity 7/72, crypto 0/72
- `by_vol_regime`: low 7/48, mid 0/48, high 0/48
- Best cell: SPY, low-vol tercile, `range_window=10, confirm_bars=3,
  max_hold_days=25`, Sharpe 1.949

## Single-config validation (Step 7), best grid config

| Symbol | Sharpe (full sample) | Threshold | Passed | Max Drawdown | Threshold | Passed |
|---|---|---|---|---|---|---|
| SPY | 0.151 | 1.0 | No | 0.346 | 0.25 | No |
| QQQ | 0.282 | 1.0 | No | 0.305 | 0.25 | No |

## Verdict

Both Sharpe and max-drawdown fail decisively at the best grid config on
both equities; crypto rejected outright. The bare probe-then-reclaim
mechanic fires on ordinary noise breakdowns without genuine
accumulation-structure context, leading to large drawdowns from false
"springs" during real trend breakdowns. Not accepted.

**Notes for future loops:** the source explicitly notes volume/spread
confirmation matters -- a future revisit could add a low-volume-on-probe +
rising-volume-on-reclaim filter to separate genuine springs from noise.
