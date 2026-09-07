# Holt-Winters Forecast Trend — Backtest Report (2026-09-08)

## Hypothesis
Per TradingView's "Holt-Winters Forecast Bands" indicator description, a
Holt double-exponential-smoothing (level + trend) forecast line provides a
"directional bias" for trend-following. This implementation uses Holt's
two-parameter linear-trend model (no seasonality term, since daily
financial series lack a fixed seasonal cycle): entry when close crosses
above the prior bar's one-step-ahead forecast AND the model's own trend
component is positive; exit on cross below the forecast, trend turning
non-positive, or a 10-day time-stop.

Source: https://www.tradingview.com/script/rcrVhyqk-Holt-Winters-Forecast-Bands/

## Grid test summary (alpha=[0.1,0.2,0.3] x beta=[0.05,0.1,0.2] x
max_hold_days=[10,20], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3,
2018-2026)

- total_cells=216, passed=56, pass_fraction=0.259
- by_asset_class: equity 56/108, crypto 0/108 (decisive crypto rejection)
- by_vol_regime: low 32/72, mid 14/72, high 10/72 (edge concentrated in
  low-vol regime, but present across all three)
- best_cell: SPY low-vol, alpha=0.3/beta=0.05/max_hold_days=10, Sharpe 2.56
- worst_cell: QQQ high-vol, Sharpe -0.78

## Single-config validators (alpha=0.3, beta=0.05, max_hold_days=10)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full-sample) | 0.601 FAIL | 1.003 PASS | >= 1.0 |
| Max drawdown | 0.173 PASS | 0.111 PASS | <= 0.25 |
| TC survival (5bps/trade, net Sharpe) | 0.405 FAIL (231 trades) | 0.697 PASS (221 trades) | >= 0.5 |
| Walk-forward (4-split, manual contiguous; vectorbt RangeSplitter API mismatch per prior iterations' documented workaround) | 4/4 PASS | 4/4 PASS | >= 3/4 |
| Parameter sensitivity (relative std, 4-point nearby-param sweep) | 0.088 PASS | 0.186 PASS | <= 0.5 |

Crypto (BTC/USDT, ETH/USDT): rejected decisively, 0/108 grid cells passed.

## Decision: ACCEPT (SPY only, narrow scope)

SPY passes all five validators (Sharpe pass is razor-thin at 1.003, echoing
this repo's prior "Walking the Bands" SPY razor-thin pass at 1.002).
QQQ fails full-sample Sharpe (0.601) and TC-survival (net Sharpe 0.405,
below the 0.5 floor) despite passing MDD, walk-forward, and parameter
sensitivity -- keep this strategy live for SPY only, do not apply to QQQ.
Crypto is decisively out of scope (0/108 grid cells).
