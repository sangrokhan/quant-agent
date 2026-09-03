# Mass Index Reversal Bulge (EMA-slope-filtered) — Backtest Report

**Hypothesis:** Donald Dorsey's Mass Index (25-period sum of the ratio of a
9-period EMA of the high-low range to its own double-smoothed 9-period EMA)
fires a "reversal bulge" when it climbs above 27 then drops back below
26.5, signaling a widen-then-narrow range pattern that often precedes a
trend reversal. Since non-directional, paired with a trend-slope
precondition (9-EMA sloping down before the bulge) and a price-crosses-
above-9EMA trigger for long entries; exit on price closing back below the
9-EMA.

Source: Google AI-overview + corroborating snippets from onetradejournal.com,
GoCharting, TradingSim, PineScriptForge (web_search failed 4x with a
DDGS/Yahoo TLS connection error, fell back to browser_exec Google search).

## Step 6 — Grid test (bulge_high x trend_ema_span x asset class x vol regime)

Grid: `bulge_high` in [26.0, 27.0] (bulge_low fixed at bulge_high-0.5),
`trend_ema_span` in [9, 20], symbols equity=[QQQ, SPY],
crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3. 48 cells total.

- **pass_fraction: 0.021 (1/48)** — the lowest of any strategy tested in
  this repo to date
- 5 cells returned "empty/no-trade slice" errors (the bulge+slope+trigger
  compound condition is so rare that some vol-regime slices contain zero
  trades entirely)
- by_asset_class: equity 1/24; crypto 0/24
- best_cell: QQQ, bulge_high=26.0, trend_ema_span=9, vol_regime=low, Sharpe
  1.44 (single low-vol tercile, tiny sample -- not representative)

## Full-sample Sharpe by config (QQQ, SPY)

| Config (bulge_high, trend_ema_span) | QQQ (trades, Sharpe) | SPY (trades, Sharpe) |
|---|---|---|
| 26.0, 9 | 10, -0.119 | 8, -0.730 |
| 26.0, 20 | 7, -0.289 | 6, 0.319 |
| 27.0, 9 | 2, 0.128 | 3, -0.393 |
| 27.0, 20 | 3, -0.115 | 1, 0.066 |

**Every combo on both symbols is far below the 1.0 Sharpe threshold, most
are negative.** Trade counts are extremely low (1-10 over 7.7yr) — the
compound bulge+slope+trigger condition is simply too rare and, when it
does fire, has no discernible edge in either direction.

## Outcome

**Rejected across all configs and asset classes (decisive).** No further
single-config validator suite run given the near-total grid failure and
uniformly poor/negative full-sample Sharpe — this is one of the clearest
rejections in the repo's history. The non-directional nature of the Mass
Index combined with a rare compound trigger condition produces too few
signals to establish any statistical edge; a future loop attempting a
Mass-Index-based idea should likely test it purely as a volatility-
regime/timing FILTER on top of an already-edge-having signal, rather than
as a standalone entry trigger.
