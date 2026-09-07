# Backtest Report: Elder Ray Index (Bull Power / Bear Power) Trend-Following

**Strategy file:** `strategies/2026-09-08_elder_ray_bull_bear_power.py`
**Date:** 2026-09-08

## Hypothesis

Per https://www.daytrading.com/elder-ray-index (Dr. Alexander Elder's Elder
Ray Index): Bull Power = Daily High - EMA(n); Bear Power = Daily Low -
EMA(n). Long entry when Bear Power is negative but increasing (selling
pressure fading) AND Bull Power is increasing (buying pressure
strengthening), confirmed by an EMA-slope trend filter (source's own
recommendation). Exit on the mirrored condition (source's short-entry rule,
repurposed as exit) or a max_hold_days time-stop. First Elder Ray strategy
in this repo.

## Grid test (Step 6)

`param_grid={"ema_period": [13,21,34], "max_hold_days": [10,20]}`,
symbols equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01. 72 cells total.

- **pass_fraction: 10/72 (13.9%)**
- by_asset_class: equity 10/36, crypto 0/36 (decisive fail)
- by_vol_regime: low 8/24, mid 0/24, high 2/24
- best_cell: ema_period=21, max_hold_days=10, SPY, low-vol, Sharpe 2.05
- worst_cell: ema_period=21, max_hold_days=10, SPY, mid-vol, Sharpe -1.23
  (same config, different regime -- a red flag for regime-dependence)
- Per-symbol/param breakdown showed ema_period=34 was the most consistent
  SPY config (2/3 vol regimes passing) vs ema_period=21 (1/3) despite
  having the single best cell.

## Single-config validation (Step 7), config ema_period=34/max_hold_days=10, SPY, full sample 2019-2026

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL (near-miss) | 0.921 | 1.0 |
| Max drawdown | PASS | 2.69% | 25% |
| Transaction-cost survival (10bps/trade, 36 trades) | PASS | net Sharpe 0.564 | 0.5 |
| Parameter sensitivity | **FAIL (decisive)** | relative_std 1.373 | 0.5 |
| Walk-forward | ERROR (vectorbt `utils.splitting` attribute missing -- same known dependency issue as 2026-09-08-002/006; not evaluated) |

Parameter grid (Sharpe by config, full-sample SPY) -- highly unstable:
```
ema_period=13, mhd=10/20: 0.198
ema_period=21, mhd=10/20: -0.147  (negative!)
ema_period=34, mhd=10/20: 0.921
```
(max_hold_days had zero effect at any ema_period in this sample -- exits
were always triggered by the indicator condition before the time-stop.)

## Decision: REJECT

Best single config (ema_period=34) is a near-miss on Sharpe (0.921) with
excellent MDD and passing TC-survival, but parameter sensitivity fails
decisively (relative_std 1.373 vs 0.5 threshold): moving the EMA period
from 34 to 21 flips the strategy from solidly positive to outright
negative Sharpe (-0.147), and 13 gives yet another different middling
result. This is not simply "narrower but honest" (per RESEARCH_LOOP.md
Step 6 framing) -- it's a genuinely unstable/curve-fit-looking response
surface where the "good" parameter value is an isolated island rather than
part of a smooth region, which is exactly the failure mode
check_parameter_sensitivity exists to catch. Crypto is decisively 0/36
across the whole grid. Worth a note for a future revisit: try widening the
EMA grid search only around 30-40 to see if there's a genuine plateau there
that a coarser [13,21,34] grid missed, rather than assuming the whole
indicator family is dead.
