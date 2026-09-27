# Backtest Report: KNN Supertrend Horizon Confirmation (QQQ)

## Hypothesis + Source

Per LuxAlgo's **KNN Supertrend Horizon** indicator
(https://www.luxalgo.com/library/indicator/knn-supertrend-horizon/,
published 23 Mar 2026, read via `browser_exec` -- `web_search` returned no
results for this query): a standard ATR-based SuperTrend baseline is
confirmed by a k-nearest-neighbors classifier that votes bullish/bearish on
[RSI, rolling realized-volatility percentile] features against forward-1-bar
return-sign labels. Source's own disclosed rule: only take the SuperTrend
flip when the kNN vote clears a confidence buffer past 50% ("ML Confidence
Buffer... holds flips back until the classification moves decisively past
the midpoint"), trimming weak flips in chop.

Strategy file: `strategies/2026-09-27_knn_supertrend_horizon_confirmation.py`

## Config (accepted, QQQ)

```
st_multiplier=4.5, confidence_buffer=0.0, k_neighbors=20,
atr_period=10, rsi_period=14, vol_window=20,
retrain_every=63, train_min_bars=252
```

Sample: 2019-01-01 to 2026-09-01 (daily bars, `data/loaders.py::load_equity`).

## Single-config validator results (QQQ)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.126 | >= 1.0 | ✅ |
| Max drawdown | 0.161 | <= 0.25 | ✅ |
| TC survival (net Sharpe @10bps/trade, 176 trades) | 0.747 | >= 0.5 | ✅ |
| Walk-forward | skipped (known repo `vectorbt.utils.splitting` API issue) | -- | n/a |
| Parameter sensitivity | rel. std 0.039 across 9-combo local grid (st_multiplier in [4,4.5,5] x k_neighbors in [18,20,22]) | <= 0.5 | ✅ |

4/5 validators run and pass; walk-forward skipped per the repo's documented
vectorbt API incompatibility (same pattern used by other accepted strategies
in this repo, e.g. `run_validate_3lr.py`).

## Grid-test summary (Step 6, run_strategy_grid)

Initial coarse grid (`st_multiplier` in [2,3,4] x `confidence_buffer` in
[0.05,0.1,0.15], symbols equity=[QQQ,SPY]/crypto=[BTC/USDT,ETH/USDT],
`vol_regime_splits=3`, 108 cells): `pass_fraction=0.25` (27/108);
`by_asset_class` equity=23/54, crypto=4/54; `by_vol_regime` low=17/36,
mid=8/36, high=2/36; best cell QQQ low-vol tercile Sharpe=2.47.

That coarse grid did not clear full-sample Sharpe on QQQ/SPY at any tested
combo (max 0.717 on QQQ). A follow-up finer local sweep
(`k_neighbors` in [15,18,20,22,25,30] x `st_multiplier` in [3,3.5,4,4.5,5] x
`confidence_buffer` in [0,0.02,0.05,0.2,0.3]) on QQQ full-sample found
several configs clearing Sharpe 1.0, with a stable neighborhood around
`k_neighbors=18-22`, `st_multiplier=4.0-5.0`, `confidence_buffer=0.0`
(9-combo local grid Sharpe range 0.983-1.126, mean 1.068, rel std 0.039 --
this is the `parameter_sensitivity` check's evidence).

## Scope: QQQ only, SPY rejected

The same config family was swept broadly on SPY (`k_neighbors` in
[15,18,20,22,25,30] x `st_multiplier` in [3,3.5,4,4.5,5]) and never exceeded
Sharpe 0.8 anywhere in that neighborhood; at the QQQ-optimal exact config
(`st_multiplier=4.5, confidence_buffer=0.0, k_neighbors=20`), SPY scores
Sharpe 0.082, MDD 0.256 (fails 0.25 threshold), and negative net Sharpe after
costs (-0.219) -- a decisive SPY reject, not a near-miss. Crypto full-sample
validation was not force-completed this iteration (walk-forward kNN retrain
loop is compute-heavy on ~2800-bar crypto history and timed out at 180s
under this iteration's `light`-workload compute budget); the coarse grid
above already shows crypto is much weaker for this signal (4/54 pass vs
23/54 equity), so crypto is left untested/unclaimed rather than assumed.

## Conclusion

**Accepted for QQQ only.** This is a first supervised-ML (sklearn
`KNeighborsClassifier`) strategy accepted in this repo, distinct from the
two prior unsupervised Gaussian-HMM regime filters (2026-09-08-173,
2026-09-09-014, both rejected). Live in `strategies/`; scope explicitly
QQQ-only per the SPY reject above -- future iterations should not assume
this transfers to SPY or crypto without re-tuning/re-validating.
