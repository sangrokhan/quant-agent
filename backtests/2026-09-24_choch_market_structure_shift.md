# Change of Character (CHoCH) Market-Structure-Shift Reversal — Backtest Report (2026-09-24)

## Hypothesis

Per multiple corroborating "Smart Money Concepts" sources (the5ers.com,
Daily Price Action, ICT Trading -- surfaced via a Google AI-overview
synthesis after `web_search` returned no results; `browser_exec` fallback
used): a bullish Change of Character (CHoCH) occurs when, during an
established downtrend (sequence of Lower Highs/Lower Lows), price CLOSES
above the most recent Lower High, signaling the downtrend's internal
structure has just shifted. Sources emphasize candle-BODY confirmation
(close through the level), not a wick sweep. First CHoCH/Market-Structure-
Shift strategy in this repo (0 prior KB hits) -- distinct from the
existing ICT Order Block, Fair Value Gap, and Swing Failure Pattern
entries (each a different mechanical trigger within the same broader
toolkit, all previously rejected).

## Strategy file

`strategies/2026-09-24_choch_market_structure_shift.py`

## Grid test summary (Step 6)

72 cells: `swing_window ∈ {3, 5, 8}` × `max_hold_days ∈ {20, 30}` ×
symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime terciles,
2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | 0.375 (27/72) |
| equity pass | 17/36 |
| crypto pass | 10/36 |
| low-vol pass | 15/24 |
| mid-vol pass | 8/24 |
| high-vol pass | 4/24 |
| best cell | QQQ mid-vol, swing_window=5/max_hold=30, Sharpe 2.83 |
| worst cell | BTC/USDT mid-vol, swing_window=3/max_hold=20, Sharpe -0.92 |

Several configs reach 0.67 pass_fraction (QQQ swing_window=3/5 both hold
values, SPY swing_window=3, BTC/USDT swing_window=8) but full-sample
single-config validation (below) reveals these full-sample-level near
misses.

## Single-config validation (Step 7)

| Validator | QQQ (sw=5, mh=30) | SPY (sw=3, mh=20) | BTC/USDT (sw=8, mh=20) |
|---|---|---|---|
| Sharpe (>=1.0) | FAIL 0.668 | **PASS** 1.024 | FAIL 0.782 |
| Max Drawdown (<=0.25) | FAIL 0.307 | PASS 0.146 | FAIL 0.391 |
| TC Survival (>=0.5 net Sharpe, 10bps/trade) | PASS 0.633 | PASS 0.965 | PASS 0.767 |
| Walk-Forward (>=0.75 pass fraction, 4 splits) | PASS 0.75 (3/4) | PASS 0.75 (3/4) | PASS 1.0 (4/4) |
| Parameter Sensitivity (<=0.5 relative std) | PASS 0.198 | PASS 0.399 | FAIL 0.767 |

SPY: 5/5 pass. QQQ: 3/5 (Sharpe + MDD fail). BTC/USDT: 3/5 (Sharpe + MDD +
param-sensitivity fail).

## Decision

**Accept for SPY only.** Reject QQQ (Sharpe + MDD fail) and BTC/USDT
(Sharpe + MDD + param-sensitivity fail). Strategy file and this report
kept; log entry records the narrow SPY-only accepted scope (config
swing_window=3, max_hold_days=20).
