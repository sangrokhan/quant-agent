# Backtest Report: CMO Trend-Pullback Resumption

**Strategy file:** `strategies/2026-09-06_cmo_trend_pullback_resume.py`
**Date:** 2026-09-06

## Hypothesis

Per [TradingSim's CMO guide](https://www.tradingsim.com/blog/chande-momentum-oscillator-cmo-technical-indicator),
the Chande Momentum Oscillator (CMO) works best as a confirmation layer
rather than a standalone trigger: in an established uptrend, wait for the
CMO to pull back toward zero (or mildly negative) and then turn back up,
signaling momentum resuming with the trend. This is distinct from the two
prior CMO variants already tested in this repo: fixed +-50 threshold
oversold-reversal (2026-09-04-055, rejected) and CMO/signal-line crossover
(2026-09-05-064, rejected). Long entry: close > SMA(trend_window) AND CMO
dipped to <= pullback_threshold within the trailing pullback_lookback bars
AND CMO turning up today. Exit: CMO >= overbought_threshold (50), trend
break, or max_hold_days time-stop.

## Grid test (Step 6)

`param_grid={cmo_period:[9,14,20], trend_window:[50,200], pullback_lookback:[5,10]}`,
symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2019-2026, 144 total cells.

- **pass_fraction = 0.146 (21/144)**
- by_asset_class: equity 21/72 (0.292), crypto 0/72 (0.0)
- by_vol_regime: low 16/48 (0.333), mid 0/48 (0.0), high 5/48 (0.104)
- best_cell: `cmo_period=9, trend_window=200, pullback_lookback=10`, SPY,
  low-vol, Sharpe=2.72
- worst_cell: `cmo_period=20, trend_window=200, pullback_lookback=5`, QQQ,
  low-vol, Sharpe=-0.55

The signal is entirely equity-side and concentrated in the low-vol tercile;
crypto rejected decisively across all 72 cells.

## Single-config validation (Step 7): best config = `cmo_period=9, trend_window=200, pullback_lookback=10`

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Walk-fwd pass frac | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | 0.675 (FAIL, thr 1.0) | 0.184 (PASS, thr 0.25) | 0.523 (PASS, thr 0.5) | 0.75 (PASS, thr 0.75) | 0.227 (PASS, thr 0.5) |
| SPY | 0.939 (FAIL, thr 1.0) | 0.148 (PASS, thr 0.25) | 0.662 (PASS, thr 0.5) | 0.75 (PASS, thr 0.75) | 0.182 (PASS, thr 0.5) |

Note: `check_walk_forward` in `validation/validators.py` hits the
pre-existing `vbt.utils.splitting` API bug (documented in several prior
backtest reports, e.g. `2026-09-03_btc_absolute_momentum.md`) -- walk-forward
here was computed manually (4 contiguous-slice split, Sharpe>0 per split)
as the established workaround.

## Decision: REJECT

Full-sample Sharpe fails the >=1.0 threshold on both QQQ (0.675) and SPY
(0.939, a near-miss). All other single-config validators pass, and the
grid's best cell (SPY low-vol) reaches Sharpe 2.72, but that strength does
not generalize across vol regimes on the full sample -- the pullback-and-turn
trigger fires too infrequently/broadly-timed on the full multi-regime
history to clear the primary Sharpe bar. Worth a future revisit narrowly
scoped to low-vol-regime-gated deployment only (SPY), but not accepted as a
broad full-sample strategy.
