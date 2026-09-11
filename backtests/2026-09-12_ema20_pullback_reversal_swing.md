# 20-EMA Pullback Reversal Swing — Backtest Report

**Date:** 2026-09-12
**Strategy file:** `strategies/2026-09-12_ema20_pullback_reversal_swing.py`
**Source:** https://www.tradezella.com/blog/swing-trading-strategies ("Strategy 1: Mean Reversion to the 20 EMA")

## Hypothesis

Per the source: in stocks above their 200-EMA (established uptrend), a shallow
pullback to within ~2-3% of the 20-EMA, with RSI(14) in a mild 40-60 band
(not oversold-capitulation), low pullback volume (no distribution), and a
bullish/reversal close, marks a low-risk continuation entry. Exit if price
closes below the 20-EMA for 2 consecutive days (trend-break invalidation),
or after a 15-day time-stop.

## Best config (from grid search)

`pullback_pct=0.03, rsi_low=40, rsi_high=60` (other params at defaults:
`ema_fast=20, ema_trend=200, rsi_window=14, vol_window=20,
exit_confirm_days=2, max_hold_days=15`)

## Single-config validator results (2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass | Param sensitivity (rel. std) |
|---|---|---|---|---|---|
| SPY | 1.221 (pass, thr 1.0) | 13.6% (pass, thr 25%) | 0.932 (pass, thr 0.5) | 4/4 (pass) | 0.109 (pass, thr 0.5) |
| QQQ | 1.058 (pass, thr 1.0) | 20.9% (pass, thr 25%) | 0.863 (pass, thr 0.5) | 3/4 =0.75 (pass, thr 0.75) | 0.119 (pass, thr 0.5) |

All 5 validators pass on both SPY and QQQ.

## Grid-test summary (2019-01-01 to 2026-09-01)

Grid: `pullback_pct in {0.015, 0.02, 0.03} x rsi_low in {35, 40} x rsi_high in
{55, 60}`, symbols `{QQQ, SPY} x {BTC/USDT, ETH/USDT}`, vol_regime_splits=3.
144 total cells (min_sharpe=1.0, max_mdd=0.25 per-cell thresholds).

- Overall pass_fraction: 0.201 (29/144)
- By asset class: equity 29/72 passed; **crypto 0/72 passed (decisive reject)**
- By vol regime: low 11/48, mid 8/48, high 10/48
- Best cell: SPY, pullback_pct=0.03/rsi_low=40/rsi_high=60, low-vol, Sharpe 2.54
- Worst cell: BTC/USDT, pullback_pct=0.015/rsi_low=40/rsi_high=55, low-vol, Sharpe -0.06

## Decision: ACCEPT (equity only — SPY, QQQ)

All validators pass for both equity symbols at the best grid config. Crypto
is decisively rejected across the whole grid (0/72) — the strategy's
regime/logic (200-EMA uptrend pullback with RSI mean band + low-volume
filter) does not transfer to BTC/ETH; scope this strategy to equities only.
