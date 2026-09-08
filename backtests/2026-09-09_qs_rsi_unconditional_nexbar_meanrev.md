# QS RSI Unconditional Mean Reversion (Next-Bar Execution) — QQQ/SPY/BTC/ETH

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_qs_rsi_unconditional_nexbar_meanrev.py`
**Outcome:** REJECTED (all symbols)

## Hypothesis

Per QuantifiedStrategies.com's "QS RSI: A Simple Indicator for Short-Term
Mean Reversion" (https://www.quantifiedstrategies.com/qs-rsi-a-simple-indicator-for-short-term-mean-reversion/,
formula fully disclosed): QS RSI = mean(RSI(3), IBS*100, 5-day range
position*100). The article's own worked example: buy next open when QS
RSI<10, sell next open when QS RSI>65 — UNCONDITIONAL (no trend filter).
This tests that unconditional form (with tighter thresholds and a
next-bar-execution lag), distinct from this repo's already-accepted
2026-09-04-164 QS RSI variant (entry=20/exit=70, WITH a 200-day SMA
uptrend gate).

## Grid test (Step 6)

`param_grid`: entry_threshold in [8, 10, 15], exit_threshold in [55, 65, 75]
`symbols`: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
`vol_regime_splits`: 3 (low/mid/high realized-vol terciles)
Total cells: 108, passed: 15, **pass_fraction: 0.139**

By asset class: equity 15/54 passed, crypto 0/54 passed (decisive crypto
rejection — expected, no overnight-session gap structure for this
range-position-based indicator to exploit differently than intraday bars).

By vol regime: low 13/36, mid 0/36, high 2/36 — edge concentrated almost
entirely in low-vol regime; unconditional signal loses money in mid/high
vol.

Best cell: entry=15/exit=55, SPY, low-vol regime, Sharpe 2.19.
Worst cell: entry=8/exit=55, QQQ, mid-vol regime, Sharpe -0.45.

## Single-config validation (Step 7), best grid config entry=15/exit=55

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.322 (FAIL) | 0.530 (FAIL) | >= 1.0 |
| Max drawdown | 0.211 (PASS) | 0.283 (FAIL) | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.203 net Sharpe (FAIL) | 0.388 net Sharpe (FAIL) | >= 0.5 |
| Walk-forward (4 splits) | 0.5 (FAIL) | 0.75 (PASS, borderline) | >= 0.75 |
| Parameter sensitivity | rel_std 0.190 (PASS) | rel_std 0.252 (PASS) | <= 0.5 |

## Decision

**REJECTED.** Full-sample Sharpe decisively misses threshold on both QQQ
and SPY (0.32 / 0.53 vs 1.0 required) despite an attractive best-cell grid
result concentrated in the low-vol regime. The unconditional (no
trend-filter) form loses its edge outside low-vol conditions — mid-vol
regime is a complete washout (0/36 grid cells pass) and crypto is decisive
0/54. This confirms the value of the trend filter used in the
already-accepted 2026-09-04-164 variant; the trend gate isn't optional
window-dressing, it is load-bearing for QS RSI's edge. Not worth a
refinement iteration since -164 already captures the accepted form of this
indicator family for QQQ/SPY.

## Source

https://www.quantifiedstrategies.com/qs-rsi-a-simple-indicator-for-short-term-mean-reversion/
