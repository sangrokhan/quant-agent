# Backtest Report: Anchored VWAP (swing-low) crossover + ATR hard stop-loss

**Strategy file:** `strategies/2026-09-06_anchored_vwap_swinglow_atrstop.py`
**Date:** 2026-09-06
**Symbols tested:** QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
**Timeframe:** 1d

## Hypothesis

Direct revisit of near-miss 2026-09-04-138 (rolling-swing-low Anchored VWAP
crossover, rejected: Sharpe 0.836 vs 1.0, max_drawdown 0.298 vs 0.25, both
narrowly failing; clean TC-survival/walk-forward/param-sensitivity on a
non-thin sample of 175 trades). Per trader-dale.com's "Master Anchored
VWAP: 3 Simple Strategies for Smarter Trading" (source URL:
https://www.trader-dale.com/master-anchored-vwap-3-simple-strategies-for-smarter-trading/,
newly visited this iteration), the stated stop-loss rule for AVWAP setups
is: "Place your stop loss just beyond the opposite side of the AVWAP line
(or outside the outer standard deviation band if using AVWAP bands)." This
strategy adds a hard ATR-based protective stop (entry_close -
atr_stop_mult * ATR(atr_window)) on top of the *unchanged* prior
entry/exit crossover logic, isolating whether a stop-loss alone fixes the
excess-drawdown rejection reason.

## Step 6 grid summary (QQQ/SPY/BTC-USDT/ETH-USDT, atr_stop_mult in
[1.5, 2.0, 3.0] x lookback in [20, 40], vol_regime_splits=3)

```
total_cells: 72
passed_cells: 15
pass_fraction: 0.2083
by_asset_class: equity 15/36, crypto 0/36
by_vol_regime: low 12/24, mid 3/24, high 0/24
best_cell: atr_stop_mult=1.5, lookback=40, QQQ, low-vol, sharpe=2.676
worst_cell: atr_stop_mult=2.0, lookback=20, SPY, mid-vol, sharpe=-0.366
```

Same broad pattern as the pre-stop version: equity-only, low-vol
concentrated, crypto categorically 0/36. The stop-loss did not change the
qualitative shape of where this strategy works.

## Single-config validation (best grid config: atr_stop_mult=1.5,
lookback=40, max_hold_days=60, atr_window=14; QQQ full sample 2019-01-01 to
2026-09-01, 116 trades)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.945 | >= 1.0 |
| Max drawdown | **FAIL** | 0.282 | <= 0.25 |
| Transaction cost survival (10bps/trade) | PASS | 0.822 net Sharpe | >= 0.5 |
| Walk-forward (4 contiguous splits) | PASS | 4/4 splits positive Sharpe (1.0 pass fraction) | >= 0.75 |
| Parameter sensitivity (6-cell QQQ sweep, atr_stop_mult x lookback) | PASS | relative_std 0.079 | <= 0.5 |

Improvement vs. the pre-stop strategy (2026-09-04-138): Sharpe 0.836 ->
0.945, max_drawdown 0.298 -> 0.282. Both metrics moved in the right
direction but neither cleared its threshold -- the ATR stop trimmed some
drawdown and improved risk-adjusted return, but not enough. Still a
near-miss, now closer than before.

## Decision: REJECTED

Both primary validators (Sharpe, max drawdown) fail on the best grid
config, despite passing TC-survival, walk-forward, and parameter
sensitivity cleanly. The strategy file and this report are kept as a
record of a rejected (near-miss, incrementally improved) attempt -- not a
live strategy.
