# Backtest Report: Kaufman Wide Ranging Days (ATR-Confirmed Outside Day)

**Strategy file:** `strategies/2026-09-12_kaufman_wide_ranging_days.py`
**Hypothesis ID:** 2026-09-12-193
**Source:** https://financial-hacker.com/petra-on-programming-short-term-candle-patterns/
(Petra Volkova, covering Perry Kaufman's S&C January 2021 candle-pattern article)

## Hypothesis

"Wide Ranging Days": an Outside Day (higher high AND lower low than prior
bar) additionally gated by (a) volatility expansion -- today's True Range
exceeds 1.5x the 20-day ATR -- and (b) close landing in the upper (for
bullish) 25% of today's own range. Trend-filtered (SMA), fixed
holding-period exit (source's own 1-5 day test methodology).

## Grid test (Step 6): `atr_mult` in {1.2,1.5,2.0} x `hold_days` in
{2,3,5}, QQQ/SPY equity + BTC/USDT, ETH/USDT crypto, vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.037** (4/108 cells) -- the weakest grid
  result recorded in this repo to date.
- **By asset class:** equity 4/54; crypto 0/54 (decisive).
- **By vol regime:** low 4/36, mid 0/36, high 0/36.
- **Best cell:** QQQ, low-vol, `atr_mult=1.5, hold_days=5` (Sharpe 1.15).
- **Worst cell:** SPY, high-vol, `atr_mult=1.2, hold_days=2` (Sharpe -1.07).
- Signal is also very sparse (single-config sanity check on SPY 2019-2026:
  only 7 trades over ~7.5 years) -- the compound condition (outside day +
  volatility expansion + close-quartile + trend filter) is highly
  restrictive.

## Decision: **REJECT (decisive)** -- no single-config validator run

Given the extremely low grid pass_fraction (0.037, the lowest recorded in
this repo) and the sparse trade count even in the best-performing
configuration, this strategy is rejected without a full Step 7
single-config validator run. Combined with the also-decisively-rejected
Key Reversal pattern (2026-09-12-191, same source, pass_fraction 0.056),
this confirms Kaufman's candle-pattern family (as adapted to daily-bar
QQQ/SPY/BTC/ETH in this repo) does not produce a robust tradeable edge,
consistent with the source's own explicitly skeptical framing.
