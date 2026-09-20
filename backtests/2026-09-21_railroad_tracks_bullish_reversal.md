# Backtest Report: Bullish Railroad Tracks Candlestick Reversal

**Strategy file:** `strategies/2026-09-21_railroad_tracks_bullish_reversal.py`
**Date:** 2026-09-21
**Hypothesis source:** Google AI-overview synthesis of TradingView's
"Railway Tracks Pattern Trading Strategy" writeup and multiple corroborating
candlestick-pattern education sources (accessed via `browser_exec` Google
SERP fallback after `web_search` DDGS backend TLS-errored on this query).

## Hypothesis

The "Railroad Tracks" (a.k.a. "Railway Tracks") pattern is a 2-candle
reversal setup: two consecutive candles with long, roughly-equal-length
real bodies (each covering >= `min_body_ratio` of that candle's high-low
range) of opposite colors. The bullish variant appears at a downtrend
bottom: a long bearish candle followed by a long bullish candle of similar
length. Sources' trading rule: enter long above the second candle's high
(breakout confirmation), stop below its low, target a fixed R-multiple.
Adapted here to daily close-based execution (no intrabar stop orders):
entry on close breaking above bar2's high within `confirm_window` bars,
exit on close falling below bar2's low or a `max_hold_days` time-stop.

First "railroad tracks"/"railway tracks" pattern strategy in this repo (0
prior KB hits) — distinct from Bullish Engulfing (no equal-length
requirement), Piercing Pattern (close above bar1's midpoint, no
equal-length requirement), and Harami (containment, opposite relationship).

## Grid test (Step 6)

`param_grid={"min_body_ratio": [0.6, 0.7, 0.8], "confirm_window": [2, 3, 5]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2018-01-01 to 2026-09-01.

- **Overall pass_fraction: 11/108 = 0.102**
- By asset class: equity 11/54 passed, crypto 0/54 (decisive reject)
- By vol regime: low 3/36, mid 2/36, high 6/36 (best in high-vol regime)
- Best cell: SPY, min_body_ratio=0.7/confirm_window=2, high-vol regime,
  Sharpe 2.06
- Worst cell: BTC/USDT, min_body_ratio=0.6/confirm_window=2, low-vol
  regime, Sharpe -0.76

Best shared config across full-sample averaging: SPY
(min_body_ratio=0.7, confirm_window=2/3/5 all similar, avg Sharpe ~0.93-1.15).

## Single-config validators (SPY, min_body_ratio=0.7, confirm_window=2)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.159 | >= 1.0 |
| Max drawdown | PASS | 0.024 | <= 0.25 |
| Transaction cost survival (10bps, 5 trades) | PASS | 1.124 | >= 0.5 |
| Walk-forward (manual 4-split) | **FAIL** | 0/4 splits (2 splits had zero trades, 1 negative, only Q4 positive) | >= 0.75 pass fraction |
| Parameter sensitivity | PASS | relative_std 0.369 | <= 0.5 |

QQQ (min_body_ratio=0.6, confirm_window=2): Sharpe 0.704 (FAIL, < 1.0
threshold), MDD 0.103 (PASS), TC-survival 0.663 (PASS, 11 trades).

## Decision: REJECTED

Despite a strong full-sample Sharpe and clean max-drawdown/parameter-
sensitivity results on SPY, this pattern occurs extremely rarely (only 5
trades on SPY, 11 on QQQ, over 8.7 years) — the walk-forward split
decisively fails because 2 of 4 quarters had zero pattern occurrences at
all, so the entire full-sample Sharpe is driven by a handful of lucky
trades concentrated in one quarter, not a robust repeatable edge. Crypto
rejected decisively (0/54 grid cells). This is a classic "too few trades to
trust" near-miss — the pattern's rarity itself (requiring a downtrend +
two long, equal-length, opposite-colored candles simultaneously) makes it
statistically unreliable to validate even with clean Sharpe/MDD numbers.

**Note for future loops:** if revisited, consider a much longer sample
period, a coarser body-length/equal-length tolerance to get more
occurrences, or pooling the pattern across a larger equity universe rather
than testing single-symbol.
