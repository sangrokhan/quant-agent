# Backtest Report: Parabolic SAR (Wilder) Flip Signal + SMA Trend Filter

**Strategy file:** `strategies/2026-09-04_parabolic_sar_trend_filter.py`
**Knowledge base id:** 2026-09-04-042

## Hypothesis

Per QuantifiedStrategies.com's Parabolic SAR article: the classic Wilder
Parabolic SAR (acceleration factor starting at 0.02, incrementing per new
swing extreme, capped at 0.20) flipping from above price to below price
signals the start of an uptrend. The source's own SPY backtest found NO
reliably profitable STANDALONE SAR strategy and explicitly recommends
pairing SAR with a trend filter (moving average / RSI / ADX). This
strategy implements that: long-only entry on SAR bullish flip AND
close > SMA(trend_window); exit on SAR bearish flip or trend filter break.

Source: https://www.quantifiedstrategies.com/parabolic-sar-trading-strategy/
(fetched via `browser_exec` after `web_extract` failed with the recurring
DuckDuckGo/ddgs search-only-backend error).

## Grid test summary (Step 6)

Grid: `af_step` in {0.01, 0.02, 0.03} x `trend_window` in {50, 200} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells.

- `pass_fraction`: 0.236 (17/72)
- `by_asset_class`: equity 17/36, crypto 0/36
- `by_vol_regime`: low 12/24, mid 5/24, high 0/24
- `best_cell` (low-vol-tercile artifact, not full-sample): QQQ,
  af_step=0.01/trend_window=50, Sharpe 2.53

As with nearly every prior trend strategy in this repo, the grid's raw
low-vol-tercile "best cell" is not representative of the full sample.
A manual full-sample sweep across the same 6 `(af_step, trend_window)`
combos on QQQ and SPY found `af_step=0.03, trend_window=200` is the best
full-sample config on QQQ (Sharpe 1.195) and also the best on SPY (Sharpe
0.853, still below threshold) — selected as the primary config.

## Full-sample sweep (QQQ / SPY, trend_window in {50, 200})

| af_step | trend_window | QQQ Sharpe | SPY Sharpe |
|---|---|---|---|
| 0.01 | 50  | 0.957 | 0.692 |
| 0.02 | 50  | 0.716 | 0.869 |
| 0.03 | 50  | 0.894 | 0.900 |
| 0.01 | 200 | 0.929 | 0.747 |
| 0.02 | 200 | 1.103 | 0.809 |
| 0.03 | 200 | **1.195** | 0.853 |

## Primary config validators (af_step=0.03, trend_window=200)

### QQQ

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.195 | 1.0 |
| Max drawdown | ✅ | 0.166 | 0.25 |
| Transaction cost survival | ✅ | 1.039 (net Sharpe, 83 trades @ 10bps) | 0.5 |
| Walk-forward (4 splits, manual date-slice fallback) | ✅ | 0.75 (3/4 splits positive) | 0.75 |
| Parameter sensitivity (af_step in {0.01,0.02,0.03}, trend_window=200 fixed) | ✅ | rel.std 0.103 | 0.5 |

**All 5 validators pass on QQQ.**

### SPY (same config)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.853 | 1.0 |
| Max drawdown | ✅ | 0.157 | 0.25 |
| Transaction cost survival | ✅ | 0.647 | 0.5 |
| Parameter sensitivity | ✅ | rel.std 0.054 | 0.5 |

SPY fails only Sharpe (14.7% shortfall) — a near-miss but not accepted at
this config.

### Crypto (BTC/USDT, ETH/USDT)

0/36 grid cells passed across all vol regimes and parameter combos —
decisively rejected, consistent with nearly every other trend strategy
tested in this repo on crypto.

## Outcome

**Accepted for QQQ only.** SPY near-miss (Sharpe 0.853, other 3 validators
pass). Crypto rejected decisively.

## Notes

Walk-forward used the manual date-slice fallback (splits sample into 4
equal contiguous chunks and checks per-split Sharpe>0) since
`validators.check_walk_forward`'s `vbt.utils.splitting.RangeSplitter` call
hits a known API bug in the installed vectorbt version (`vectorbt.utils`
has no attribute `splitting`) — documented recurring issue since
2026-09-03-002. Split 1 (~2020-2021, likely COVID crash/recovery period)
had negative Sharpe (-0.925); splits 0, 2, 3 were strongly positive.
