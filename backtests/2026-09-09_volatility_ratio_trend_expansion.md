# Volatility Ratio Trend-Expansion Filter (Long-Only) — Backtest Report

**Date:** 2026-09-08 (iteration 2, cron trigger 2026-09-09)
**Strategy file:** `strategies/2026-09-09_volatility_ratio_trend_expansion.py`
**Source:** https://theindicatorlab.com/reviews/volatility-ratio/

## Hypothesis

The "Volatility Ratio" (VR) indicator measures directional price movement
relative to the asset's own recent volatility: `VR = |close -
close.shift(vr_length)| / ATR(vr_length)` — i.e. how many ATRs price has
travelled net over the lookback window. VR expanding past a threshold
signals a genuine directional move (not noise); a subsequent contraction
below a lower threshold signals the move has exhausted. Distinct from the
already-tested Historical Volatility Ratio (2026-09-06-109, a pure
vol-of-vol ratio with no directional-displacement numerator) since this
VR's numerator is the actual net price displacement — a volatility-
normalized MOMENTUM oscillator, not a vol-of-vol ratio.

Per the source's own stated best setup: pairing a VR cross above 1.5-2.0
with an uptrend filter (price above a long EMA) caught strong trends
early; exit fully only when VR drops below a materially lower band
(source used 0.5) — an asymmetric hysteresis band rather than a single
crossunder level.

## Config (best shared equity config)

```
vr_length=30, entry_threshold=2.0, exit_threshold=0.5, trend_window=100
```

## Grid test summary (Step 6)

Grid: `vr_length in {14,20,30}`, `entry_threshold in {1.2,1.5,2.0}`,
`exit_threshold in {0.5,0.8}`, `trend_window in {100,200}` x symbols
`{QQQ,SPY,BTC/USDT,ETH/USDT}` x vol_regime_splits=3 (low/mid/high
terciles). 2018-01-01 to 2026-09-01.

- `total_cells=432`, `passed_cells=81`, `pass_fraction=0.1875`
- `by_asset_class`: equity 81/216 passed; **crypto 0/216 (decisive
  reject for crypto)**
- `by_vol_regime`: low 70/144, mid 7/144, high 4/144 — this strategy's
  edge is concentrated almost entirely in **low-volatility regimes**,
  consistent with this repo's broader accumulated finding that most
  trend/momentum strategies here work mainly in low-vol conditions.
- `best_cell`: SPY, vr_length=30/entry_threshold=2.0/exit_threshold=0.5/
  trend_window=100, low-vol regime, Sharpe 2.71.
- `worst_cell`: SPY, vr_length=30/entry_threshold=2.0/exit_threshold=0.8/
  trend_window=200, mid-vol regime, Sharpe -0.76.

## Single-config validator results (full sample, shared config)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.014 (PASS) | 1.092 (PASS) | >= 1.0 |
| Max drawdown | 0.156 (PASS) | 0.161 (PASS) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.951 (PASS) | 0.978 (PASS) | >= 0.5 |
| Parameter sensitivity (relative std, 3x3 grid around config) | 0.123 (PASS) | 0.219 (PASS) | <= 0.5 |
| Walk-forward (manual 4-split substitute — `check_walk_forward` in `validators.py` errors with `module 'vectorbt.utils' has no attribute 'splitting'`, a pre-existing repo bug unrelated to this strategy) | 4/4 splits Sharpe > 0 (PASS) | 4/4 splits Sharpe > 0 (PASS) | >= 3/4 |

Manual walk-forward split Sharpes (4 equal contiguous chunks of the full
sample, no gap/embargo, no re-optimization per split — same fixed
config): QQQ `[0.953, 0.446, 1.381, 0.673]`; SPY `[0.877, 0.728, 1.328,
1.476]`. All 8 splits positive.

Number of trades over full sample: QQQ 45, SPY 53 — both comfortably
above minimum trade-count thresholds for the transaction-cost check to
be meaningful.

## Decision

**ACCEPTED for equity (QQQ, SPY)** at the shared config
`vr_length=30/entry_threshold=2.0/exit_threshold=0.5/trend_window=100`.
**REJECTED for crypto** (BTC/USDT, ETH/USDT) — decisive 0/216 grid cells,
consistent with the vast majority of trend/momentum-family strategies in
this repo failing on 24/7 crypto markets.

Scope caveat for future loops: this strategy's edge concentrates almost
entirely in low-volatility regimes (70/144 low-vol passes vs. 7/144 mid
and 4/144 high) — treat it as a low-vol-regime equity trend-confirmation
filter, not a general-purpose all-weather strategy.
