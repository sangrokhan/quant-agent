# Takuri Line (Bulkowski Candlestick) — Uptrend-Retrace + Confirmation

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_takuri_line_uptrend_retrace_confirmed.py`
**Source:** https://thepatternsite.com/TakuriLine.html (Thomas Bulkowski,
`browser_exec` fallback — `web_search` DDGS backend returned unrelated
results for this domain this iteration).

## Hypothesis

Bulkowski's Takuri Line: a small-bodied candle with a lower shadow >=3x
body height and minimal upper shadow, in a downward price trend, signals
a bullish reversal 66% of the time (source's own tested stat, overall
rank 47/103). Source's own "Three Trading Tidbits" disclose its strongest
context: "as part of a downward retracement in an up trend" plus an
explicit confirmation rule ("wait for price to close higher the next
day"). This strategy implements the source-preferred, stricter variant
(uptrend filter, tighter 3x wick ratio, next-day confirmation) — the same
approach that succeeded for this cron trigger's earlier "Above the
Stomach" strategy.

First Takuri Line strategy in this repo (0 prior KB index hits) — distinct
from the already-rejected generic Hammer (2026-09-06-147, 2x wick ratio,
plain downtrend gate, no confirmation bar).

## Grid test summary (`grid_summary_takuri_line.json`)

- 216 cells: `param_grid={wick_to_body_ratio:[2.5,3.0,3.5],
  retrace_lookback:[3,5,8], max_hold_days:[5,10]}`, symbols equity
  `[QQQ, SPY]` + crypto `[BTC/USDT, ETH/USDT]`, `vol_regime_splits=3`,
  2019-2026.
- **pass_fraction: 0.019 (4/216)** — decisive reject
- by_asset_class: equity 4/108, crypto 0/108 (decisive reject)
- by_vol_regime: low 4/72, mid 0/72, high 0/72
- best_cell: equity QQQ low-vol, Sharpe 1.49 (wick_to_body_ratio=2.5,
  retrace_lookback=3, max_hold_days=10)

## Full-sample confirmation (best-cell config, 2019-2026)

| Symbol | Trades | Sharpe |
|---|---|---|
| QQQ | 2 | 0.853 (fails 1.0 threshold) |
| SPY | 0 | n/a (no signals at all) |

## Outcome: **REJECTED**

The combined uptrend + retracement + strict-3x-wick-ratio + minimal-upper-
shadow + next-day-confirmation AND-gate is far too restrictive: only 2
qualifying trades on QQQ over 7.7 years and 0 on SPY. Consistent with the
already-rejected generic Hammer's own finding that this candlestick shape
generates too few tradeable signals under a tight numeric definition. Not
pursued further this iteration (grid decisively confirms the full-sample
result — no near-miss worth rescuing).
