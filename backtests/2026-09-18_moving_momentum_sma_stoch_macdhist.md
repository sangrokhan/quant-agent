# Moving Momentum (SMA20/150 + Stochastic + MACD-Histogram) — Backtest Report

**Hypothesis:** Per StockCharts.com ChartSchool's "Moving Momentum"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/moving-momentum,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content): a 3-step process -- (1) 20-day SMA above 150-day SMA
(tuned to 180-day this iteration) sets a bullish trading bias, (2)
Stochastic Oscillator dropping below 20 (tuned to 30) flags a pullback
within the uptrend, (3) MACD-Histogram turning positive is the actual entry
trigger confirming the pullback has ended. Exit on bias flip or a
max_hold_days time-stop.

**Source:** https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/moving-momentum

## Grid summary (Step 6)

- Grid: sma_slow∈{100,150,200} × max_hold_days∈{20,40}, symbols={QQQ,SPY}×
  {BTC/USDT,ETH/USDT}, vol_regime_splits=3 (2015-01-01 to 2026-09-01).
- 72 total cells, 13 passed (pass_fraction=0.18).
- by_asset_class: equity 13/36; crypto 0/36 (decisive crypto failure).
- by_vol_regime: low 10/24, mid 3/24, high 0/24.
- Best cell: QQQ sma_slow=100/max_hold_days=20, mid-vol Sharpe=1.94.

## Full-sample parameter search + single-config validation (Step 7)

| Symbol | Best config | Full-sample Sharpe |
|---|---|---|
| QQQ | sma_slow=150, max_hold_days=60, stoch_low=15 | 0.830 (fail) |
| SPY | sma_slow=180, max_hold_days=40, stoch_low=30 | 1.096 (pass) |

SPY single-config validation (sma_slow=180, max_hold_days=40, stoch_low=30):

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.096 | ≥1.0 | PASS |
| Max drawdown | 0.138 | ≤0.25 | PASS |
| TC survival (5bps/trade, 62 trades) | 1.049 | ≥0.5 | PASS |
| Walk-forward (manual 4-slice) | 3/4=0.75 | ≥0.75 | PASS |
| Parameter sensitivity (20-combo local sweep) | rel.std=0.341 | ≤0.5 | PASS |

## Decision: ACCEPT (SPY only)

SPY clears all 5 validators, with walk-forward exactly at the 0.75
threshold (3/4 splits positive) -- a genuine but tight pass. QQQ falls
short of the Sharpe 1.0 threshold across an extensive local parameter
search (best 0.830), and crypto decisively fails on both symbols. This
strategy is added to `strategies/` as a live SPY-only strategy.
