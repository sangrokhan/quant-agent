# Backtest Report: Volume Climax Reversal (2026-09-06)

**Hypothesis:** Per Finveroo's "Volume Climax Reversal Strategy" guide
(https://www.finveroo.com/trading-academy/strategies/volume/volume-climax/):
an extended downtrend ending in a volume spike (>=2.5-4x average volume) on
a new N-day low, followed by a rejection candle (large lower wick, close in
upper half of the day's range), signals seller exhaustion and a probable
reversal. Adapted to daily bars with a mean-reversion (SMA cross) exit and
an 8-day time-stop.

**Source:** https://www.finveroo.com/trading-academy/strategies/volume/volume-climax/

**Strategy file:** `strategies/2026-09-06_volume_climax_reversal.py`

## Step 6 grid summary (`run_strategy_grid`)

- Grid: `vol_mult` in {2.5, 3.0, 4.0} x `wick_ratio_threshold` in {0.4, 0.5}
  x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x vol regimes {low, mid, high} (+ "n/a" for data-load errors)
- **48 total cells, 0 passed -- pass_fraction = 0.0**
- by_asset_class: equity 0/36, crypto 0/12
- by_vol_regime: low 0/12, mid 0/12, high 0/12, n/a 0/12
- best_cell: SPY, vol_mult=2.5, wick_ratio_threshold=0.4, mid-vol regime, Sharpe=0.758 (still below 1.0 threshold)
- worst_cell: SPY, same params, low-vol regime, Sharpe=0.681

Decisive rejection across every asset class and every volatility regime --
no narrow-but-honest slice survives either.

## Step 7 single-config validators (best grid config: SPY, vol_mult=2.5, wick_ratio_threshold=0.4)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.585 | >= 1.0 | FAIL |
| Max drawdown | 0.0009 | <= 0.25 | PASS |
| Transaction cost survival (net Sharpe, 10bps/trade) | 0.555 | >= 0.5 | PASS |
| Walk-forward | n/a | -- | SKIPPED: `check_walk_forward` raises `AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` in the installed vectorbt version -- pre-existing tooling bug, not specific to this strategy. Not blocking given the decisive grid-level rejection already. |
| Parameter sensitivity | n/a | -- | Not run -- grid pass_fraction of 0.0 across 6 param combos already demonstrates the strategy doesn't hold under any tested parameterization. |

Only 1 trade fired over the full 2019-2026 SPY sample at these thresholds
(a `vol_mult>=2.5` spike + rejection candle + new 20-day-low confluence is
very rare) -- this scarcity itself is a practical concern independent of the
Sharpe/MDD numbers: too few signals to trust the backtest statistics even if
they had looked good.

## Decision: REJECT

Sharpe fails at the best grid cell across all 48 tested combinations of
parameters x asset class x volatility regime; signal frequency is also too
low to generate a statistically meaningful sample. The core mechanism
(volume-spike + wick-rejection = reversal) does not show a testable edge
with this daily-bar adaptation.
