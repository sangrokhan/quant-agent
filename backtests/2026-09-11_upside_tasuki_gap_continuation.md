# Upside Tasuki Gap Bullish Continuation — Backtest Report

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-11_upside_tasuki_gap_continuation.py`
**Source:** https://enlightenedstocktrading.com/upside-tasuki-gap-candlestick-pattern/

## Hypothesis

3-candle bullish continuation pattern: candle1 strong bullish; candle2
bullish, gaps entirely above candle1's range; candle3 bearish, opens within
candle2's body, closes back into the gap zone but does NOT fully close it
(close3 > high1) -- signals buyers remain in control. Entry after candle3
closes, stop below candle3's low, trend-gated (close1 > SMA(trend_window)).

## Grid test summary (Step 6)

`scripts/run_grid_tasuki.py` — param grid `trend_window∈{20,50,100}`,
`min_body_pct∈{0.3,0.5}`, `max_hold_days∈{5,10}` × symbols
`{QQQ,SPY,BTC/USDT,ETH/USDT}` × 3 vol-regime terciles (144 total cells).

- **pass_fraction: 0.118** (17/144)
- **by_asset_class:** equity 17/72 passed, **crypto 0/72 passed**
- **by_vol_regime:** low 12/48, mid 0/48, high 5/48
- **best_cell:** QQQ, trend_window=20/min_body_pct=0.3/max_hold_days=10, low-vol, Sharpe 1.62

## Single-config validators (Step 7) — best grid config (trend_window=20, min_body_pct=0.3, max_hold_days=10), full sample 2010-2026

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | # trades |
|---|---|---|---|---|---|---|
| QQQ | **0.329 (FAIL)** | 0.028 (pass) | **0.288 (FAIL)** | **0.5 (FAIL, thr 0.75)** | 0.128 (pass) | 4 |
| SPY | **0.612 (FAIL)** | 0.019 (pass) | 0.577 (pass) | 1.0 (pass) | **0.928 (FAIL)** | 5 |

Extremely rare pattern on daily equity bars (only 4-5 valid signals over
16 years for QQQ/SPY) -- far too few trades for a statistically meaningful
edge; both symbols fail multiple validators (QQQ fails Sharpe/TC/walk-forward,
SPY fails Sharpe/param-sensitivity due to the tiny sample making Sharpe
highly parameter-dependent).

## Decision: REJECTED

Both QQQ and SPY fail the Sharpe threshold outright, and each fails at
least one additional validator (QQQ: TC-survival + walk-forward; SPY:
parameter sensitivity). Trade count (4-5 over 16 years) is too low for
any of these metrics to be statistically reliable in either direction --
this is a data-sparsity rejection more than a decisive "this pattern has
no edge" finding. Crypto decisively rejected across the whole grid (0/72).

Future revisit: the low-vol/QQQ Sharpe 1.62 in the grid's best cell is
likely noise given the tiny trade count; this pattern would need a much
longer lookback window, intraday bars, or a broader stock universe (not
just QQQ/SPY) to gather enough occurrences for a meaningful test.
