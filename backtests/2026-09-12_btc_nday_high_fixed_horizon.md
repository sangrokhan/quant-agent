# BTC/Equity N-day-high fixed-horizon breakout — REJECTED

**Hypothesis:** Quantpedia "Revisiting Trend-following and Mean-reversion
Strategies in Bitcoin" (12 Sep 2024),
https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/?a=6080
— buying on a new x-day high and holding for the same x-day horizon
("MAX strategy") remained effective for BTC out to Aug 2024, esp. at x=10.

**Implementation:** `strategies/2026-09-12_btc_nday_high_fixed_horizon.py`
(`generate_signals`/`generate_returns`, params `lookback`, `hold_days`).

## Grid test (validation/grid_test.py, vol_regime_splits=3)

param_grid: lookback=[10,20,30], hold_days=[5,10,20]; symbols:
equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]; 2018-01-01..2026-09-01.

- total_cells=108, passed=28, pass_fraction=0.259
- by_asset_class: equity 28/54 (0.52), crypto 0/54 (0.0)
- by_vol_regime: low 18/36, mid 9/36, high 1/36
- best_cell: lookback=30, hold_days=20, SPY, low-vol, Sharpe=2.57
- worst_cell: lookback=30, hold_days=20, QQQ, high-vol, Sharpe=-0.39

## Single-config validators (best grid config: lookback=30, hold_days=20)

| Symbol | Full-sample Sharpe | Passed (>=1.0) | Max Drawdown | Passed (<=0.25) |
|---|---|---|---|---|
| SPY | 0.745 | No | 0.197 | Yes |
| QQQ | 0.709 | No | 0.286 | No |
| BTC/USDT | 0.161 | No | 0.524 | No |
| ETH/USDT | 0.249 | No | 0.618 | No |

## Verdict: REJECTED

Full-sample Sharpe fails the >=1.0 threshold on every symbol despite a
promising grid pass fraction concentrated in low-vol equity cells (52%
equity, 0% crypto). Consistent with recurring pattern in this log: grid
per-cell (short-window, vol-tercile-sliced) Sharpe often looks attractive
in isolated low-vol slices but the honest full-sample number does not clear
bar. Crypto decisively fails (0/54 grid cells, Sharpe 0.16-0.25, MDD
52-62%) — fixed-horizon breakout holding is a poor fit for BTC/ETH's larger
drawdown/whipsaw profile vs. equities. Walk-forward/parameter-sensitivity
not run given full-sample Sharpe already fails decisively (workload=max but
no value in further validators once the primary threshold is missed this
badly).
