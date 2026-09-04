# Backtest Report: Bullish Engulfing Candlestick Reversal, Trend-Filtered

**Strategy file:** `strategies/2026-09-04_bullish_engulfing_trend.py`
**Date:** 2026-09-04
**Source:** Google AI-overview (LuxAlgo/TradingView/apptrading.ai consensus)
(retrieved via browser_exec after web_search DDGS/Yahoo TLS failure)

## Hypothesis

A Bullish Engulfing pattern (short-term decline, bearish Day1 candle,
bullish Day2 candle fully engulfing Day1's real body) within a long-term
uptrend (close > SMA200) signals a reversal worth a long entry; exit on
mean-reversion to the 5d SMA, trend break, or max_hold_days.

## Grid test summary (decline_days x 4 symbols x 3 vol terciles = 24 cells)

- pass_fraction: **8.3%** (2/24) -- weak
- by_asset_class: equity 2/12 (17%), crypto 0/12 (0%)
- by_vol_regime: low 1/8, mid 1/8, high 0/8

## Full-sample single-config metrics

| Symbol | decline_days | Sharpe | Pass | MDD   | Pass | Trades |
|--------|--------------|--------|------|-------|------|--------|
| SPY    | 1            | 0.297  | No   | 0.053 | Yes  | 46     |
| SPY    | 2            | -0.133 | No   | 0.059 | Yes  | 20     |
| QQQ    | 1            | 0.519  | No   | 0.046 | Yes  | 35     |
| QQQ    | 2            | 0.154  | No   | 0.046 | Yes  | 21     |

## Decision: REJECTED (all symbols)

No configuration comes close to the Sharpe threshold (best: QQQ at
decline_days=1, Sharpe 0.52). MDD is very tight everywhere (4.6-5.9%),
confirming the pattern doesn't produce large losing trades, but there's
also no meaningful risk-adjusted edge to harvest -- consistent with a broad
body of retail-trading literature (also echoed in some of the source pages
themselves, e.g. "Bullish Engulfing Pattern Tested 100 TIMES") suggesting
single-pattern candlestick signals traded in isolation, even with a trend
filter, rarely produce a standalone statistical edge; they are more
commonly used as one confirming input among several (e.g. combined with an
oscillator extreme or support/resistance level) rather than a sufficient
signal on their own. The requirement to also pass a strict body-containment
test (open/close relationships across two specific candles) additionally
limits trade frequency (only 20-46 trades over 7.7yr), making the strategy
statistically thin regardless of edge quality.

Future idea: combine with an oversold oscillator reading (e.g. RSI<30) at
the time of the pattern, per the "confirmation" pattern used successfully
elsewhere in this repo (e.g. OBV divergence -088's EMA-crossback
confirmation requirement), rather than relying on the candlestick shape
alone.
