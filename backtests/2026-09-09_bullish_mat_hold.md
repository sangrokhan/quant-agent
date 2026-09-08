# Bullish Mat Hold (5-Candle Continuation) — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_bullish_mat_hold.py`
**Source:** https://wrtrading.com/technical-analysis/charts/candlestick/pattern/mat-hold/

## Hypothesis

The Mat Hold is a 5-candle TREND-CONTINUATION pattern (not a reversal, the
first such construction tested in this repo's candlestick family): a
strong bullish impulse candle, 3 smaller consolidation candles that hold
above the impulse candle's low, then a bullish breakout candle closing
above the impulse candle's high, confirming continuation within an
established uptrend.

## Grid test (Step 6)

`param_grid={"impulse_body_mult": [1.0,1.3,1.6], "max_hold_days": [10,15]}`,
symbols QQQ/SPY/BTC-USDT/ETH-USDT, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01.

- **72 total cells, 13 passed (pass_fraction 0.181)**
- By asset class: equity 13/36, **crypto 0/36 (decisive fail)**
- By vol regime: low 5/24, mid 8/24, **high 0/24**
- Best cell: QQQ, impulse_body_mult=1.6/max_hold_days=15, mid-vol regime, Sharpe 1.90

## Single-config validators (impulse_body_mult=1.6, max_hold_days=15)

| Symbol | Trades | Sharpe (full) | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | 36 | 0.616 **FAIL** (thr 1.0) | 0.123 PASS | 0.548 PASS | 0.75 pass_fraction PASS | 0.313 PASS |
| SPY | 33 | 0.498 **FAIL** (thr 1.0) | 0.098 PASS | 0.402 **FAIL** (thr 0.5) | 0.75 pass_fraction PASS | 0.289 PASS |

## Decision: REJECTED

Full-sample Sharpe misses the 1.0 threshold on both QQQ (0.616) and SPY
(0.498), despite acceptable trade frequency (33-36 trades), clean MDD, and
stable parameter sensitivity. The grid's best cell (Sharpe 1.90) is
concentrated in the mid-vol tercile only (0/24 in high-vol, 5/24 in
low-vol) — a regime-specific artifact that doesn't generalize to the full
sample. Crypto failed all 36 grid cells. This is a genuine near-miss
(unlike several decisive 0/72 rejections earlier this cron trigger) but
falls short of the acceptance bar; a future revisit could try gating entry
on the mid-vol regime specifically or tightening the consolidation
structural requirement, but this iteration's straightforward literal
implementation of the source's rule does not clear the bar as-is.
