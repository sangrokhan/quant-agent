# VIDYA Price Crossover — Backtest Report (2026-09-24)

## Hypothesis

Chande's VIDYA (Variable Index Dynamic Average) — an EMA whose smoothing
constant is scaled by `|CMO|/100` (Chande Momentum Oscillator) — speeds up
in trending/volatile conditions and slows down in flat/choppy conditions.
Trading rule: long entry when close crosses above VIDYA, exit when close
crosses below VIDYA, with a slope-magnitude filter suppressing crossovers
when the VIDYA line itself is flat (source's own noted refinement to reduce
whipsaw).

Source: Google AI-overview synthesis (browser_exec Google SERP fallback —
`web_search` DDGS backend TLS-errored on this query), corroborated by
StrategyQuant, ArrowAlgo, and cTrader help pages. First VIDYA-family
strategy in this repo (0 prior knowledge-base hits for "VIDYA").

## Strategy file

`strategies/2026-09-24_vidya_price_crossover.py`

## Grid test summary (Step 6)

144 cells: `vidya_period ∈ {10, 14, 20} × cmo_period ∈ {9, 14} ×
slope_threshold ∈ {0.0, 0.01}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` ×
3 vol-regime terciles, 2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | 0.333 (48/144) |
| equity pass | 36/72 (QQQ-dominant) |
| crypto pass | 12/72 |
| low-vol pass | 36/48 |
| mid-vol pass | 12/48 |
| high-vol pass | 0/48 |
| best cell | QQQ low-vol, vidya_period=20/cmo_period=14/slope=0.01, Sharpe 2.80 |
| worst cell | QQQ high-vol, vidya_period=20/cmo_period=9/slope=0.01, Sharpe -1.16 |

Notably robust QQQ pattern: 2/3 vol-regime cells pass at **every single**
parameter combination tested (12/12 configs at 0.67 pass rate) — unusually
stable across the grid compared to most tested candidates this trigger.

## Single-config validation (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param-sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | vidya_period=10, cmo_period=14, slope_threshold=0.01, max_hold=40 | 1.170 ✅ | 0.158 ✅ | 1.109 ✅ | 0.75 ✅ (exactly at threshold, 3/4 splits) | 0.099 ✅ | **ACCEPT** |

39 trades over the full sample; parameter-sensitivity very stable
(relative_std 0.099, well under the 0.5 threshold).

## Decision

**Accepted for QQQ.** SPY and crypto were not pursued to full single-config
validation this iteration — the grid showed a clearly QQQ-dominant pattern
(SPY only 4/12 configs passing vs QQQ's 12/12), so SPY/crypto are flagged
as candidates for a future per-symbol parameter retune rather than
force-tested this iteration.
