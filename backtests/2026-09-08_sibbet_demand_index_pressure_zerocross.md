# 2026-09-08 Sibbet Demand Index Zero-Cross Trend Strategy (QQQ) — REJECTED

**Hypothesis:** James Sibbet's Demand Index (a leading volume-price
oscillator), reconstructed from the TradingView conair script description
(https://www.tradingview.com/script/CY3t5FqX-Demand-Index-James-Sibbet/ --
confirms H+L+2C weighted price and 0.375 exponential factor) and LuxAlgo's
Demand Index library page
(https://www.luxalgo.com/library/indicator/demand-index/ -- confirms the
volume/volatility normalization and buy/sell pressure split mechanics):
volume normalized by its recent average is split into buying/selling
pressure by the size/direction of a volatility-scaled weighted-price move,
EMA-smoothed, combined into a signed zero-centered ratio. Entry when the
index crosses above zero (buying pressure dominates) gated by an SMA trend
filter; exit on the mirror cross, trend break, or time-stop.

**Important caveat:** this is a documented best-effort reconstruction, not
an exact replication of Sibbet's original 1986 Stocks & Commodities
20+-column spreadsheet formula (not freely available online this
iteration -- Investopedia 404'd, Scribd PDF not fetched, Sierra Chart URL
stale). See notes for full source list.

Source: https://www.tradingview.com/script/CY3t5FqX-Demand-Index-James-Sibbet/,
https://www.luxalgo.com/library/indicator/demand-index/. First Demand Index
strategy in this repo.

## Grid test (Step 6)

`param_grid = {trend_window: [50, 100], max_hold_days: [10, 15, 20]}`,
`symbols = {equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Overall pass fraction: 12/72 (16.7%)**
- By asset class: equity 12/36, crypto 0/36 (decisive crypto rejection)
- By vol regime: low 12/24, **mid 0/24, high 0/24** (low-vol-only edge)
- Best cell: QQQ, low-vol, `trend_window=50, max_hold_days=20`, Sharpe 2.67
- Worst cell: QQQ, high-vol, `trend_window=50, max_hold_days=20`, Sharpe -0.84

## Single-config validators (Step 7): QQQ, trend_window=50, max_hold_days=20, full sample 2019-2026

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ FAIL | 0.536 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 17.7% | ≤ 25% |
| Transaction cost survival (10bps/trade, 115 trades) | ❌ FAIL | net Sharpe 0.330 | ≥ 0.5 |
| Walk-forward (manual 4-equal-slice fallback) | ✅ PASS | 3/4 splits positive (75%) | ≥ 75% |
| Parameter sensitivity (6-point sweep: trend_window×max_hold_days) | ✅ PASS | relative_std 0.237 | ≤ 0.5 |

115 trades over the full sample is a high turnover for a daily-bar
zero-cross strategy — the fast EMA smoothing (span=10) on the pressure
components produces frequent zero-crossings, and the 10bps/trade cost
assumption erodes the marginal edge decisively.

## Decision: REJECTED

Full-sample Sharpe misses (0.536 < 1.0) and transaction-cost survival
decisively fails (0.330 vs 0.5) despite MDD/walk-forward/param-sensitivity
all passing. The grid's low-vol-only pass pattern (12/24 low, 0/24 mid,
0/24 high) confirms the edge is narrow and concentrated, consistent with
the single-config near-uniform failure. Crypto rejected decisively (0/36).
Left in `strategies/` as a rejected record.
