# Tradewink RSI+BB+SMA200+Volume-Spike+Candle Oversold Bounce (Backtest Report — REJECTED)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_oversold_bounce_rsi_bb_volume_candle.py`
**KB id:** 2026-09-22-060

## Hypothesis

Per Tradewink's "Mean Reversion Trading: Strategy Guide with Entry Rules &
Examples" (https://www.tradewink.com/learn/mean-reversion-trading-strategy,
"The Oversold Bounce Setup (Long)" section, read via `browser_exec` this
iteration — `web_extract`'s ddgs backend cannot fetch page bodies), the
source's own disclosed 5-implementable-part entry checklist (excluding the
non-mechanical "no negative catalyst" criterion): RSI(14)<30, close at/below
lower Bollinger Band(20,2), close above SMA(200), volume>1.5x its 20-day
average, and a reversal candle (hammer/doji/bullish engulfing) on the same
bar. Exit at "return to mean" (Bollinger middle band) or a time-stop. First
strategy in this repo combining all five conditions as a single AND-gate
(prior entries tested RSI+BB+volume without trend/candle gates, or
standalone candlestick patterns without RSI+BB+volume co-gates).

## Grid test summary (Step 6)

`param_grid={rsi_oversold:[25,30,35], vol_mult:[1.5,2.0], max_hold_days:[10,15]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`
→ 144 cells total.

- **Overall pass_fraction: 0.0 (0/144) — decisive rejection.**
- By asset class: equity 0/72, crypto 0/72
- By vol regime: low 0/48, mid 0/48, high 0/48
- Best cell: BTC/USDT, rsi_oversold=30, vol_mult=1.5, max_hold_days=10,
  mid-vol, Sharpe=0.829 (still below 1.0 threshold)
- Worst cell: BTC/USDT, rsi_oversold=35, vol_mult=1.5, max_hold_days=15,
  high-vol, Sharpe=0.156
- **Root cause confirmed by direct signal check:** on QQQ full-sample
  (2018-01-01 to 2026-09-01), the 5-condition AND-gate produced **0 entry
  signals** — combining RSI oversold + BB lower-band touch + SMA(200)
  uptrend + volume spike (1.5x) + a reversal-candle OR-gate simultaneously
  is simply too restrictive on daily equity bars to ever co-occur; a
  similar sparsity issue likely explains crypto's weak Sharpe (few, noisy
  signals).

## Decision

**Reject, no single-config validation attempted.** Decisive grid failure
(0/144) with a confirmed root cause (near-zero signal frequency from
over-restrictive AND-gate) — per RESEARCH_LOOP.md Step 8, no promising
region warrants a Step 7 validator run. A future loop could revisit this
source's individual sub-components (e.g. RSI+BB alone, or volume-spike+
candle alone) with an OR-gate or relaxed condition count rather than
requiring all five simultaneously.
