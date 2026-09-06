# Hull Moving Average (HMA) Slope-Turn Trend-Following

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_hma_slope_turn_trend.py`
**KB id:** 2026-09-06-128

## Hypothesis

Alan Hull's HMA formula: HMA(n) = WMA(2·WMA(price, n/2) − WMA(price, n),
round(sqrt(n))). Per corroborating SERP snippets (usethinkscript forum,
Scribd HMA strategy summary): go long when the HMA's slope turns from
falling to rising (the "color change" moment); exit when slope turns back
down. First HMA-based strategy in this repo (a genuinely different
weighted-moving-average construction from SMA/EMA/KAMA-based strategies
already tested).

**Source:** https://www.thinkmarkets.com/en/trading-academy/forex/hull-moving-average/
(formula, browser_exec) + Google SERP snippets for the slope-turn rule
(web_search errored on this iteration's query).

## Grid test (hma_window=[10,20,30] x max_hold_days=[20,40,60], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 34/108 cells passed (equity 34/54, **crypto 0/54 decisively rejected**)
- By vol regime: low 18/36, mid 9/36, high 7/36 (works best in calm markets but has some high-vol pass cells too)
- Best avg-config: hma_window=30, max_hold_days=20, QQQ avg Sharpe 1.49

## Single-config validators (QQQ, hma_window=30, max_hold_days=20, full sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.225 | ≥ 1.0 |
| Max drawdown | PASS | 22.4% | ≤ 25% |
| TC survival (10bps, 68 trades) | PASS | net Sharpe 1.123 | ≥ 0.5 |
| Walk-forward (manual 4-split) | PASS | 4/4 splits positive | ≥ 0.75 |
| Parameter sensitivity (9-cell QQQ sweep) | PASS | relative_std 0.090 | ≤ 0.5 |

SPY sanity check at same config: Sharpe 1.241 (consistent, slightly better than QQQ).

## Decision: **ACCEPT** (equity only — QQQ/SPY)

All validators pass with a very low parameter-sensitivity relative_std
(0.090 — one of the most stable grids in this repo), and the result is
consistent across both equity tickers. Crypto is decisively rejected
(0/54). Scope: equity/QQQ+SPY only, consistent with the repo's recurring
pattern of equity-only edges.
