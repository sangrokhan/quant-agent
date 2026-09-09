# Backtest report: Elder Ray contraction-recovery + swing-high breakout confirm

**Strategy file:** `strategies/2026-09-09_elder_ray_contraction_breakout_confirm.py`
**Knowledge base id:** 2026-09-09-104
**Outcome:** REJECTED

## Hypothesis

Per Bing SERP synthesis (trendsandbreakouts.com / chartingpath.com /
protraderdashboard.com) of Alexander Elder's Bull/Bear Power rules: a long
entry needs (1) 13-EMA rising with close above it, (2) Bear Power
(Low-EMA) negative-but-rising (contraction/recovery), AND (3) an explicit
price-action confirmation -- "break above a recent swing high for longs" --
as the entry trigger, not the indicator condition alone.

## Grid test summary (Step 6)

- Grid: `ema_window` in [13, 21] x `swing_window` in [15, 20, 30] x
  `max_hold_days` in [15, 30] x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x
  3 vol terciles = 144 cells.
- `pass_fraction`: **0.021** (3/144)
- `by_asset_class`: equity 3/72 passed, crypto 0/72
- `by_vol_regime`: low 3/48, mid 0/48, high 0/48
- Best cell: SPY, low-vol tercile, `ema_window=13, swing_window=15,
  max_hold_days=30`, Sharpe 1.508
- Worst cell: QQQ, high-vol tercile, Sharpe -1.199

## Single-config validation (Step 7), best grid config

| Symbol | Sharpe (full sample) | Threshold | Passed | Max Drawdown | Threshold | Passed |
|---|---|---|---|---|---|---|
| SPY | 0.144 | 1.0 | No | 0.037 | 0.25 | Yes |
| QQQ | -0.472 | 1.0 | No | 0.049 | 0.25 | Yes |

## Verdict

Full-sample Sharpe fails decisively on both equities despite the best
grid cell (a narrow low-vol tercile slice) looking attractive. The
triple AND-gate (trend + BP recovery + swing breakout) fires too rarely
to produce a broad, robust edge -- the low-vol pass was a slice artifact.
Crypto rejected outright (0/72). Not accepted.

**Notes for future loops:** if Elder-Ray is revisited again, consider
relaxing the strict AND-gate to an OR/2-of-3 vote structure rather than
requiring all three conditions simultaneously.
