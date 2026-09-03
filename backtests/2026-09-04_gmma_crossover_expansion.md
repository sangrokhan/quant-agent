# Backtest Report: GMMA Crossover with Expansion Confirmation

**Strategy file:** `strategies/2026-09-04_gmma_crossover_expansion.py`
**Knowledge base id:** 2026-09-04-062

## Hypothesis

Per Capital.com's GMMA (Guppy Multiple Moving Average) guide (Daryl Guppy):
two clusters of 6 EMAs each — short-term (3,5,8,10,12,15) representing
trader activity, long-term (30,35,40,45,50,60) representing investor
behavior. Long entry when the short-term EMA-group average crosses above
the long-term EMA-group average AND the spread (short_avg - long_avg) is
expanding over a lookback window (ribbon divergence confirming trend
strength, per source's explicit "must expand apart" caveat); exit on the
reverse crossover.

Source: https://capital.com/en-int/learn/technical-analysis/gmma-indicator
(QuantifiedStrategies' own GMMA article 404'd; web_search failed with the
recurring DDGS/Yahoo TLS connection error, fell back to browser_exec).

## Grid test summary (validation/grid_test.py)

- Grid: `expansion_lookback` in {2,3,5} x symbols {QQQ,SPY,BTC/USDT,ETH/USDT}
  x 3 vol-regime terciles = 36 cells.
- pass_fraction: 0.25 (9/36)
- by_asset_class: equity 9/18, crypto 0/18
- by_vol_regime: low 6/12, mid 3/12, high 0/12
- best_cell: QQQ, expansion_lookback=3, low-vol tercile, Sharpe 2.68
- worst_cell: QQQ, expansion_lookback=5, high-vol tercile, Sharpe -0.58

## Full-sample sweep (expansion_lookback in {2,3,5}, QQQ/SPY, 2019-2026)

| Symbol | lb=2 | lb=3 | lb=5 |
|---|---|---|---|
| QQQ | 1.047 | **1.088** | 0.925 |
| SPY | 1.081 | **1.066** | 1.052 |

Primary config selected: `expansion_lookback=3` (best on QQQ, near-best on SPY).

## Single-config validator suite (primary config, expansion_lookback=3)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | **1.088** (pass, thr 1.0) | **1.066** (pass, thr 1.0) |
| Max drawdown | **0.189** (pass, thr 0.25) | **0.166** (pass, thr 0.25) |
| TC survival (net Sharpe, 10bps x 25/27 trades) | **1.060** (pass, thr 0.5) | **1.026** (pass, thr 0.5) |
| Walk-forward (4 manual date-slices, 3/4 pos req.) | 4/4 splits positive (pass) | 3/4 splits positive (pass, exactly at threshold) |
| Parameter sensitivity (lb in {2,3,5}) | rel.std 0.068 (pass, thr 0.5) | rel.std 0.011 (pass, thr 0.5) |

All 5 validators pass on both QQQ and SPY.

## Outcome

**Accepted (QQQ and SPY).** Crypto (BTC/USDT, ETH/USDT) rejected decisively
(0/18 grid cells) — consistent with this repo's overwhelming pattern of
equity-only trend/crossover strategies.

## Notes

Novelty: distinct from every prior single/dual-MA crossover in this repo
(VWMA -060, HMA -026, KAMA -048, Vortex -040, Supertrend -053, SMA/EMA
variants) — GMMA uses the SPREAD/expansion between two GROUPS of 6 EMAs
each as a trend-strength confirmation signal, not a single fast/slow pair
touch. Clean dual-symbol accept (25-27 trades over 7.7yr on each), similar
pattern to VWMA -060, DPO -056, Supertrend -053 dual accepts.
