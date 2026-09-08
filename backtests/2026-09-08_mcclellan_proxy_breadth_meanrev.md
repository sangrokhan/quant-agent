# Backtest Report: McClellan-Proxy Breadth Mean Reversion (2026-09-08)

**Status: REJECTED** — strategy file kept in `strategies/` as a record of a
rejected attempt, not a live strategy.

## Hypothesis

Per QuantifiedStrategies.com "McClellan Oscillator and Summation Index:
Trading Strategy and Backtest Analysis"
(https://www.quantifiedstrategies.com/mcclellan-oscillator-and-summation-index/,
fetched via `browser_exec` after `web_extract` failed with a DuckDuckGo
backend error), the classic McClellan Oscillator (19d/39d EMA difference of
Nasdaq advances-minus-declines breadth) simple trading rule is: long when
the oscillator crosses below -100, sell when it crosses above +100 (source's
own SPY 1993-present backtest: weak/erratic equity curve, avg gain 1.2% over
97 trades).

Adapted single-asset (this repo's `data/loaders.py` has no market-wide
breadth feed): use the asset's own daily price-direction sign (+1/-1/0) as a
single-name breadth analog, apply the identical 19/39-day EMA-difference
construction, normalize via rolling percentile rank (lookback=252 days) and
threshold on percentile extremes instead of raw ±100 levels.

Background: https://en.wikipedia.org/wiki/McClellan_oscillator

## Single-config validator results (QQQ, best grid config: `oversold_pct=0.15`, `max_hold_days=10`)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.707 | ≥ 1.0 | ❌ |
| Max drawdown | 0.294 | ≤ 0.25 | ❌ |
| Net Sharpe after costs (10bps/trade, 85 trades) | 0.628 | ≥ 0.5 | ✅ |
| Walk-forward pass fraction (4 splits) | 1.0 | ≥ 0.75 | ✅ |
| Parameter sensitivity relative std | 0.4998 | ≤ 0.5 | ✅ |

## Grid test summary

`param_grid={oversold_pct:[0.05,0.1,0.15], max_hold_days:[10,20]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`
(2018-01-01 to 2026-09-01), 72 total cells.

- **Overall pass_fraction: 0.097** (7/72 cells)
- By asset class: equity 7/36 passed, **crypto 0/36 passed** (decisive reject)
- By vol regime: **low 7/24**, mid 0/24, high 0/24 — edge concentrated
  entirely in the low-volatility tercile
- Best cell: QQQ, low-vol, `oversold_pct=0.15/max_hold_days=10`, Sharpe 2.150
- Worst cell: BTC/USDT, mid-vol, Sharpe -0.152

## Decision

**Reject.** The full-sample QQQ Sharpe (0.707) and max drawdown (0.294) both
fail their thresholds, even at the grid's best-performing parameter
configuration. The grid breakdown confirms the source article's own caveat —
"the McClellan indicator can stay oversold for a pretty long time... like in
2008" — the strategy's edge is real but narrow (low-vol regime, equity-only),
and sustained-downtrend periods (mid/high-vol regimes) drag the full-sample
drawdown and Sharpe below threshold. Crypto rejected decisively across all
72/36 crypto cells.
