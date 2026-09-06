# Three White Soldiers Bullish Reversal (with Pullback Entry)

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_three_white_soldiers_pullback.py`
**KB id:** 2026-09-06-132

## Hypothesis

Classic candlestick pattern: three consecutive long-bodied bullish candles
after a downtrend, each opening within the prior candle's body
("staircase") and closing near its high, signals a shift from sellers to
buyers. Per ChartMill's backtest notes, enter on a minor pullback after
the third candle (not a chase entry) with a stop below the first candle's
low. First 3-bar geometric candlestick pattern tested in this repo
(distinct from single-bar patterns already tested: Bullish Engulfing,
Heikin-Ashi reversals, NR7).

**Source:** Google AI-overview synthesis (browser_exec SERP, corroborated
by ThinkMarkets and ChartMill descriptions of the pattern's identification
rules and pullback-entry/stop-loss recommendation) — search query "three
white soldiers three black crows candlestick pattern strategy specific
rules backtest".

## Grid test (long_body_mult=[1.0,1.2,1.5] x strong_close_pct=[0.7,0.8] x max_hold_days=[8,12], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- **0/144 cells passed** — fully decisive rejection.
- Best cell: long_body_mult=1.0, strong_close_pct=0.7, max_hold_days=12,
  ETH/USDT low-vol, Sharpe 0.229 (weak, far below 1.0 threshold).

## Decision: **REJECT**

Grid pass_fraction 0.0 (0/144). The pattern's strict multi-bar geometric
requirements (3 consecutive long bullish bars + staircase opens + strong
closes + prior downtrend + pullback confirmation) make it too rare to
generate a meaningful, reliably profitable edge in daily OHLC data across
either asset class. Skipped single-config validators since the grid is
fully decisive.
