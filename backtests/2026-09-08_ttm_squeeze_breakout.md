# Backtest Report: TTM Squeeze (Bollinger-inside-Keltner) Breakout

**Strategy file:** `strategies/2026-09-08_ttm_squeeze_breakout.py`
**Date:** 2026-09-08

## Hypothesis

Per https://volatilitybox.com/research/ttm-squeeze-indicator/ (John Carter's
TTM Squeeze): a volatility-compression state where 20-period Bollinger Bands
(2 std) sit fully inside 20-period Keltner Channels (1.5x ATR) for >=
min_squeeze_len bars, followed by the squeeze releasing (BB expands back
outside KC), tends to resolve into a directional breakout (source claims
~68% directional accuracy when its momentum histogram aligns with the
breakout, vs 55-60% for a naive Bollinger-Bandwidth-only squeeze). Long-only
adaptation per SAFETY.md: enter only when momentum (source's own linear-
regression-of-modified-price-oscillator histogram) is positive and rising at
the fire bar, plus close > 20-SMA price confirmation. Exit on momentum
deceleration/turning non-positive, or a max_hold_days time-stop.

## Grid test (Step 6)

`param_grid={"min_squeeze_len": [4,6,10], "max_hold_days": [7,15]}`,
symbols equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01. 72 cells total.

- **pass_fraction: 3/72 (4.2%)**
- by_asset_class: equity 3/36, crypto 0/36 (decisive fail)
- by_vol_regime: low 0/24, mid 0/24, high 3/24 (only passes in the high-vol
  tercile)
- best_cell: min_squeeze_len=4, max_hold_days=7, SPY, high-vol, Sharpe 1.26
- worst_cell: min_squeeze_len=6, max_hold_days=7, QQQ, low-vol, Sharpe -1.02

Signal is extremely sparse: default params produced only 2 trades over the
full 2019-2026 QQQ sample; even the best grid config (SPY,
min_squeeze_len=4/max_hold_days=7) produced only 6 trades full-sample.

## Single-config validation (Step 7), config min_squeeze_len=4/max_hold_days=7, SPY, full sample 2019-2026

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL (near-miss) | 0.882 | 1.0 |
| Max drawdown | PASS | 1.46% | 25% |
| Transaction-cost survival (10bps/trade, 6 trades) | PASS | net Sharpe 0.803 | 0.5 |
| Parameter sensitivity | FAIL | relative_std 0.966 | 0.5 |
| Walk-forward | skipped (workload=normal but signal is too sparse -- 6 trades full-sample makes a 4-way walk-forward split statistically meaningless; noted here rather than run) |

Parameter grid (Sharpe by config, full-sample SPY):
```
min_squeeze_len=4, max_hold_days=7:  0.882
min_squeeze_len=4, max_hold_days=15: 0.064
min_squeeze_len=6, max_hold_days=7:  0.699
min_squeeze_len=6, max_hold_days=15: -0.003
min_squeeze_len=10, max_hold_days=7:  0.699
min_squeeze_len=10, max_hold_days=15: -0.003
```

## Decision: REJECT

Grid pass_fraction only 4.2%, confined entirely to the high-vol tercile of
equities; crypto decisively 0/36. Best full-sample single-config Sharpe
(0.882) is a near-miss below the 1.0 threshold, and parameter sensitivity is
highly unstable (relative_std 0.966 vs 0.5 threshold) -- doubling
max_hold_days from 7 to 15 collapses Sharpe from ~0.7-0.9 down to
~0/negative, meaning the edge is extremely fragile to exit timing, not a
robust pattern. Trade count is also very low (6 trades at the best
full-sample config), giving low statistical confidence even in the
near-miss result. Consistent with this being a real but thin/fragile
signal rather than a durable edge -- worth flagging as a near-miss for a
future revisit (e.g. try tighter momentum-deceleration exit rather than
fixed max_hold_days, or restrict to explicit high-vol regime as a gate)
rather than a decisive dead end.
