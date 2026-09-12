# Backtest Report: Kaufman Key Reversal Candle Pattern (Trend-Filtered)

**Strategy file:** `strategies/2026-09-12_kaufman_key_reversal_trend.py`
**Hypothesis ID:** 2026-09-12-191
**Source:** https://financial-hacker.com/petra-on-programming-short-term-candle-patterns/
(Petra Volkova, covering Perry Kaufman's S&C January 2021 "New Rules for a
New Market" candle-pattern article)

## Hypothesis

"Key Reversal": an outside day (today's high > yesterday's high AND
today's low < yesterday's low) where today's close also breaks OUTSIDE
yesterday's range (close > yesterday's high for bullish). Long-only,
trend-filtered (close above trailing SMA), fixed holding period exit
(source's own methodology: 1-5 day fixed hold, no other exit rule).

## Grid test (Step 6): `trend_sma_window` in {50,80,150} x `hold_days` in
{2,3,5}, QQQ/SPY equity + BTC/USDT, ETH/USDT crypto, vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.056** (6/108 cells) -- one of the weakest
  results observed in this repo's history, well below typical accepted
  strategies (0.2-0.3+).
- **By asset class:** equity 6/54; crypto 0/54 (decisive).
- **By vol regime:** low 6/36, mid 0/36, high 0/36 -- only marginally
  functions, and only in the lowest-vol tercile.
- **Best cell:** QQQ, low-vol, `trend_sma_window=50, hold_days=5` (Sharpe
  1.67).
- **Worst cell:** SPY, mid-vol, `trend_sma_window=150, hold_days=5`
  (Sharpe -0.83).
- **Best average-Sharpe config across vol regimes:** QQQ
  `trend_sma_window=50, hold_days=5`, avg Sharpe only **0.719** -- below
  the 1.0 min_sharpe threshold even for the single best-performing
  config/symbol combination.

## Decision: **REJECT (decisive)** -- no single-config validator run

Given that even the best-performing config/symbol combination's own
across-vol-regime average Sharpe (0.719) falls short of the 1.0 minimum
threshold, and the overall grid pass_fraction (0.056) is exceptionally low,
this strategy is rejected without a full single-config Step 7 validator
run (per RESEARCH_LOOP.md Step 8 guidance to reject when validators for
the primary config would clearly fail). This is consistent with the
source's own explicitly skeptical framing ("it seems no one yet got rich
with them") of short-term candle patterns generally.
