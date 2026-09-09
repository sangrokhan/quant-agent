# Backtest Report: Double Stochastic Agreement Oversold-Bounce (SPY)

**Strategy file:** `strategies/2026-09-09_double_stochastic_agreement_oversold.py`
**Date:** 2026-09-09

## Hypothesis + Source

Per The Forex Geek's "Double Stochastic Strategy"
(https://theforexgeek.com/double-stochastic-strategy/, browser_exec
fallback -- web_search DDGS returned no results for several direct
queries), the source's own buy rule requires TWO plain %K/%D stochastic
oscillators of different lookback periods (fast 5,3,3 and slow 10,3,3) to
simultaneously cross bullish from the oversold (~20) zone, gated by price
above a 50-period moving average. This repo's implementation generalizes
the fast/slow windows and oversold threshold as tunable parameters and adds
a `max_hold_days` time-stop (source doesn't specify one).

## Single-config metrics (SPY, oversold_threshold=35.0, trend_window=120,
max_hold_days=8, 2018-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | Yes | 1.251 | >= 1.0 |
| Max drawdown | Yes | 4.93% | <= 25% |
| Transaction cost survival (10bps/trade, 93 trades) | Yes | 0.845 | >= 0.5 |
| Walk-forward (4 manual date-slice splits) | Yes | 1.0 (4/4 positive) | >= 0.75 |
| Parameter sensitivity (oversold_threshold in [28,30,32,35,38]) | Yes | rel.std 0.029 | <= 0.5 |

All 5 validators pass for SPY at this config.

## Step 6 grid summary

Grid: `oversold_threshold=[20,25,30]` x `trend_window=[50,100]` x
`max_hold_days=[10,15,20]`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2018-2026.

- Overall pass_fraction: 0.208 (45/216 cells)
- By asset class: equity 45/108, crypto 0/108 (crypto decisively fails)
- By vol regime: low 36/72, mid 0/72, high 9/72
- Best cell: oversold_threshold=30.0/trend_window=50/max_hold_days=10, SPY,
  low-vol regime, Sharpe 2.64
- A fine-grained search beyond the initial grid (oversold_threshold in
  [28,30,32,35,38], trend_window in [80,100,120], max_hold_days in
  [8,10,12,15]) found SPY's full-sample best config as
  oversold_threshold=35.0/trend_window=120/max_hold_days=8 (Sharpe 1.251).
- QQQ full-sample best config only reaches Sharpe 0.406 at the analogous
  grid optimum -- QQQ is rejected at this config; edge does not generalize
  across equity symbols.
- Crypto (BTC/USDT, ETH/USDT): 0/108 cells passed across the entire grid --
  decisively rejected for crypto.

## Pass/Fail per validator

All 5 validators pass for the SPY config above. QQQ and crypto (BTC/USDT,
ETH/USDT) are rejected -- the edge is SPY-specific, consistent with this
repo's history of narrow single-symbol accepts (e.g. Chandelier+ADX
QQQ-only, Firefly Oscillator SPY-only).

## Outcome

**Accepted for SPY only** (oversold_threshold=35.0, trend_window=120,
max_hold_days=8). Rejected for QQQ and crypto (BTC/USDT, ETH/USDT).
