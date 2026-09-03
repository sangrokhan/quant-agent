# Turtle Soup (Fade the Failed 20-Day-Low Breakdown) — Backtest Report

**Hypothesis:** The classic Turtle Soup pattern (Linda Bradford Raschke /
Laurence Connors, 1995): price makes a new N-day low, then FAILS to
continue and closes back above that level the next bar -- a false
breakout / stop-hunt. Long entry: close breaks below the rolling N-day low,
then next close moves back above that level. Exit after a fixed hold
period or a stop below the entry-day low. Explicit INVERSE of the
trend-following Donchian breakout already tested (2026-09-03-008,
2026-09-04-054) -- fades the breakout rather than following it.

Source: Google search snippets (AlchemyMarkets, Aron Groups, GrandAlgo,
Orbex, StrefaTradingu -- web_search failed 7x with a DDGS/Yahoo TLS
connection error, fell back to browser_exec immediately; two candidate
detail-page URLs, GrandAlgo and Captain Trading, both 404'd on direct
fetch, relied on visible search snippets for the concrete rule).

## Step 6 — Grid test (lookback x max_hold_days x asset class x vol regime)

Grid: `lookback` in [10, 20, 30], `max_hold_days` in [3, 5], symbols
equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3.
72 cells total.

- **pass_fraction: 0.042 (3/72)**
- by_asset_class: equity 3/36; crypto 0/36 (decisive reject)
- by_vol_regime: low 3/24; mid 0/24; high 0/24
- best_cell: SPY, lookback=10, max_hold_days=3, vol_regime=low, Sharpe 1.58
  (single tercile, not representative of the full sample)

## Full-sample Sharpe by config (QQQ, SPY)

| lookback | max_hold | QQQ Sharpe (trades) | SPY Sharpe (trades) |
|---|---|---|---|
| 10 | 3 | -0.321 (89) | -0.075 (85) |
| 10 | 5 | -0.099 (89) | -0.113 (85) |
| 20 | 3 | -0.141 (55) | -0.070 (53) |
| 20 | 5 | 0.063 (55) | -0.055 (53) |
| 30 | 3 | -0.048 (41) | -0.130 (38) |
| 30 | 5 | 0.138 (41) | -0.219 (38) |

**Every single combo on both symbols is far below the 1.0 Sharpe
threshold** — mostly negative, best case only 0.138. High trade frequency
(38-89 round-trips over 7.7yr) with no discernible net edge; on a
predominantly trending 2019-2026 sample (both QQQ and SPY spent most of
the window in secular uptrends), fading breakdowns systematically fights
the prevailing trend more often than it correctly identifies genuine
stop-hunts, consistent with sources' own caveat that the pattern works
better in range-bound/consolidating conditions than trending ones.

## Outcome

**Rejected across all configs and asset classes (decisive).** No
single-config validator suite run given the uniformly poor/negative
full-sample Sharpe across the entire grid — this confirms the sources'
own regime-dependence caveat (works in consolidation, fails in trends) on
a sample period that was mostly trending. A future loop could retest this
pattern gated by an explicit sideways/choppy-regime filter (e.g. the
Choppiness Index tested at 2026-09-04-059, or ADX<20 from -017) rather
than applying it unconditionally across all regimes.
