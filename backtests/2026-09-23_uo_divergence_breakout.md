# 2026-09-23 Ultimate Oscillator Divergence Breakout (SPY/QQQ/BTC)

## Hypothesis
Source: Google AI Overview (Korean-language SERP; search: "Ultimate
Oscillator divergence trading strategy specific rule backtest"), read via
browser_exec Google SERP fallback (web_search DDGS backend errored this
query). `suggested_workload=light`, gate usage at 94% this iteration so
scope was kept minimal (single default-config check, no full grid).

Rule: Larry Williams' original UO(7,14,28) divergence system -- bullish
divergence when price makes a lower swing low while UO makes a higher
swing low, entry confirmed by UO breaking above the intermediate peak
between the two lows; exit when UO crosses above 50 then back below 45, or
reaches 70 (overbought).

## Single-config check (default params, full period 2019-2026)

| Symbol | Sharpe | Passed (>=1.0) | Max DD | Passed (<=0.25) |
|---|---|---|---|---|
| SPY | 0.844 | No | 0.059 | Yes |
| QQQ | 0.445 | No | 0.168 | Yes |
| BTC/USDT | 0.144 | No | 0.345 | No |

## Verdict: REJECTED

Decisive miss on the default config across all three symbols (no
near-miss this time, unlike TRIX/ADX-DI/RVI earlier this trigger). Given
gate usage at 94% (near the 95% safety floor) this iteration was scoped to
a single default-parameter check rather than a full grid sweep -- if
revisited, a parameter sweep (swing_window, exit thresholds) might surface
a stronger config, but the gap to threshold (SPY 0.844 vs 1.0) is wider
than this trigger's near-misses, making a rescue less likely to succeed
without a structurally different confirmation mechanism.

Strategy file kept in `strategies/` as a rejected record. Grid test and
walk-forward/tx-cost/param-sensitivity validators skipped entirely this
iteration given the light workload + high gate usage + decisive single-
config miss.
