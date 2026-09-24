# Downside Gap Three Methods (Bulkowski Candlestick) — Contrarian Bullish

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_downside_gap_three_methods_contrarian.py`
**Source:** https://thepatternsite.com/dgtm.html (Thomas Bulkowski,
`browser_exec` fallback — `web_search` DDGS backend returned unrelated
results for this domain this iteration).

## Hypothesis

A rare case where the source's own theoretical framing and tested reality
diverge: "Downside Gap Three Methods" theoretically signals bearish
continuation (2 long black candles with a true, non-overlapping gap,
followed by a white candle that closes the gap), but source's own testing
shows it acts as a bullish reversal 62% of the time (overall rank 26/103,
"quite respectable"). This strategy trades the disclosed empirical
reality (contrarian long in a downtrend), following the same
"trade-the-numbers-not-the-label" approach already used successfully for
Three Black Crows (2026-09-07-001, though that one was ultimately
rejected on a different basis).

First Downside Gap Three Methods strategy in this repo (0 prior KB index
hits).

## Grid test summary (`grid_summary_downside_gap_three_methods.json`)

- 216 cells: `param_grid={trend_window:[30,50,100],
  min_body_pct:[0.005,0.01,0.02], max_hold_days:[5,10]}`, symbols equity
  `[QQQ, SPY]` + crypto `[BTC/USDT, ETH/USDT]`, `vol_regime_splits=3`,
  2019-2026.
- **pass_fraction: 0.0 (0/216)** — every cell has a `null` Sharpe (zero
  trades).

## Direct verification (full sample 2019-2026)

Confirmed via direct entry-count check at the loosest grid config
(trend_window=30, min_body_pct=0.005, max_hold_days=5): **0 entries** on
QQQ, SPY, AND BTC/USDT.

## Outcome: **REJECTED (feasibility dead end)**

The pattern's own strict identification rule -- a TRUE gap where candle
1's entire low-high range sits strictly above candle 2's entire range
(shadows do not overlap), immediately followed by a candle whose open
falls inside candle 2's body AND whose close falls inside candle 1's body
-- essentially never occurs on daily-bar QQQ/SPY/BTC/USDT data in this
repo's 2019-2026 sample. Source's own disclosed frequency rank (84/103,
"very rare") anticipated this: the pattern is inherently uncommon even in
Bulkowski's own much larger multi-decade, multi-stock sample, and this
repo's single-symbol daily-bar universe is far too small to produce even
one qualifying occurrence. Not pursued further -- no near-miss to rescue,
this is a hard feasibility/frequency floor, not a parameter-tuning
problem.
