# Deliberation Bearish Short (Backtest Report — REJECTED)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_deliberation_bearish_short.py`
**KB id:** 2026-09-22-010

## Hypothesis

Per ForexBee's disclosed rule
(https://forexbee.co/deliberation-candlestick-pattern/): a 3-candle
bearish reversal pattern at the top of an uptrend -- bar1 tall bullish,
bar2 opens above bar1's open and closes above bar1's high (continued
strength), bar3 has a materially smaller body than bar1 (buying momentum
stalling) while still closing bullish. Short entry on pattern
confirmation. First test of the Deliberation-specific pattern in this
repo (0 prior KB hits, distinct from Advance Block/Three White Soldiers).

## Grid test summary (Step 6)

`param_grid={shrink_ratio:[0.3,0.5,0.7], max_hold_days:[5,8,12]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3` → 108 cells total.

- **Overall pass_fraction: 0.009 (1/108) -- decisive rejection.**
- By asset class: equity 1/54, crypto 0/54 (ETH/USDT was uniformly
  strongly negative across every parameter/regime combo tested, -0.4 to
  -1.86 Sharpe)
- By vol regime: low 0/36, mid 0/36, high 1/36
- Only passing cell: QQQ, shrink_ratio=0.7, max_hold_days=8, high-vol,
  Sharpe=1.17 -- a single isolated cell, not a robust pattern across
  parameters or regimes.
- Worst cell: ETH/USDT, shrink_ratio=0.5, max_hold_days=12, mid-vol,
  Sharpe=-1.86

## Decision

**Reject, no single-config validation attempted.** The grid result is
decisive (1/108 cells pass, essentially noise-level) with no coherent
parameter region to focus a Step 7 validation on. The short-side framing
of this bullish-momentum-stalling pattern does not translate into a
systematic edge on daily QQQ/SPY/BTC/ETH bars -- crypto in particular was
consistently and strongly loss-making across every tested configuration.
