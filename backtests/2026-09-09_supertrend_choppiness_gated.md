# Backtest Report: Supertrend Stop-and-Reverse, Choppiness Index Trending Gate (QQQ)

**Strategy file:** `strategies/2026-09-09_supertrend_choppiness_gated.py`
**Date:** 2026-09-09

## Hypothesis + Source

Per TrendsAndBreakouts' Choppiness Index guide
(https://trendsandbreakouts.com/choppiness-index, browser_exec fallback --
web_search DDGS errored with a connection error for the direct query), the
Choppiness Index (CHOP) below ~38 signals a trending market suitable for
trend-following signals; the standard recommendation is to gate any
trend-following signal with a CHOP<threshold filter. This strategy gates
the Supertrend stop-and-reverse flip (already present standalone in this
repo as 2026-09-04_supertrend_flip.py) with a CHOP trending-regime filter,
testing whether the regime gate specifically helps this volatility-band
system (as opposed to the already-tested CHOP+SMA combination,
2026-09-04-059).

## Single-config metrics (QQQ, st_multiplier=4.0, trending_threshold=45.0,
max_hold_days=30, 2018-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | Yes | 1.143 | >= 1.0 |
| Max drawdown | Yes | 17.03% | <= 25% |
| Transaction cost survival (10bps/trade, 45 trades) | Yes | 1.068 | >= 0.5 |
| Walk-forward (4 manual date-slice splits) | Yes | 1.0 (4/4 positive) | >= 0.75 |
| Parameter sensitivity (st_multiplier in [3.0,3.5,4.0,4.5]) | Yes | rel.std 0.124 | <= 0.5 |

All 5 validators pass for QQQ at this config.

## Step 6 grid summary

Grid: `st_multiplier=[2.0,3.0,4.0]` x `trending_threshold=[35.0,38.0,45.0]`
x `max_hold_days=[20,30]`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2018-2026.

- Overall pass_fraction: 0.208 (45/216 cells)
- By asset class: equity 45/108, crypto 0/108 (crypto decisively fails)
- By vol regime: low 33/72, mid 12/72, high 0/72
- Best cell: st_multiplier=4.0/trending_threshold=45.0/max_hold_days=30,
  QQQ, low-vol regime, Sharpe 2.77 (also the full-sample best config)
- SPY at the same config only reaches full-sample Sharpe 0.604 --
  QQQ-specific edge, rejected for SPY.
- Crypto (BTC/USDT, ETH/USDT): 0/108 cells passed -- decisively rejected.

## Pass/Fail per validator

All 5 validators pass for the QQQ config above. SPY and crypto (BTC/USDT,
ETH/USDT) are rejected.

## Outcome

**Accepted for QQQ only** (st_multiplier=4.0, trending_threshold=45.0,
max_hold_days=30). Rejected for SPY and crypto (BTC/USDT, ETH/USDT).
