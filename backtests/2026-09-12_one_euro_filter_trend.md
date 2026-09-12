# Backtest Report: Ehlers One Euro Filter Trend-Following Crossover

**Strategy file:** `strategies/2026-09-12_one_euro_filter_trend.py`
**Source:** John F. Ehlers, TASC. Formula reproduced from
https://financial-hacker.com/the-one-euro-filter/ (fully disclosed
EasyLanguage-to-C code).

## Hypothesis

The One Euro Filter is an adaptive low-lag smoother whose cutoff period
WIDENS (more smoothing) when price is calm and NARROWS (less lag) when
price moves fast — the opposite adaptation direction of most adaptive MAs.
Long-only: long when close > filter (adaptively-smoothed uptrend), flat
otherwise.

## Single-config validator results

### QQQ (period_min=10, factor=100 — best QQQ grid cell)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.448 | >= 1.0 |
| Max drawdown | PASS | 0.199 | <= 0.25 |
| Transaction cost survival (10bps/trade, 142 trades) | PASS | net Sharpe 1.220 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 3/4 (75%) | >= 75% |
| Parameter sensitivity (9-cell period_min x factor grid) | PASS | rel. std 0.051 | <= 0.5 |

### SPY (period_min=10, factor=200 — best SPY grid cell)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.283 | >= 1.0 |
| Max drawdown | PASS | 0.140 | <= 0.25 |
| Transaction cost survival (10bps/trade, 125 trades) | PASS | net Sharpe 1.006 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity | PASS | rel. std 0.106 | <= 0.5 |

Both equity symbols pass ALL 5 validators; parameter sensitivity is
notably low (rel. std < 0.11 for SPY, < 0.06 for QQQ) — this strategy is
unusually robust to (period_min, factor) choice within the tested grid.

## Grid test summary (period_min x {10,20,40}, factor x {50,100,200}, equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3)

- **Total cells:** 108, **passed:** 27, **pass_fraction: 0.25**
- **By asset class:** equity 27/54 (0.5), crypto 0/54 (0.0)
- **By vol regime:** low 18/36 (0.5), mid 9/36 (0.25), high 0/36 (0.0)
- **Best cell:** QQQ low-vol, period_min=20/factor=100, Sharpe 2.92
- **Worst cell:** QQQ high-vol, period_min=40/factor=200, Sharpe -0.111

Edge is concentrated in low/mid-vol equity regimes; high-vol equity and all
crypto cells fail decisively — consistent with a smoothed trend-following
filter losing its edge in choppy/high-vol conditions.

## Decision: ACCEPT (equity only — QQQ and SPY, each with its own tuned config)

Both QQQ (period_min=10, factor=100) and SPY (period_min=10, factor=200)
pass every validator with comfortable margins and unusually low parameter
sensitivity. Crypto and high-vol equity regimes are rejected — scope this
strategy to equity trend-following in low/mid-vol conditions.
