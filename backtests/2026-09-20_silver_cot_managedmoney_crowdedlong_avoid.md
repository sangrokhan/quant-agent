# CFTC COT Silver Managed-Money Crowded-Long Avoidance — Backtest Report

**Hypothesis:** Silver (SLV) Managed Money speculators (CFTC Disaggregated
report category) herd into extreme net-long positions near local price
tops; when Managed Money net position (long - short) percentile-ranks in
the top decile of its trailing distribution, go flat (avoid the elevated
pullback-risk window), otherwise stay long (default-long framing —
opposite polarity from this trigger's other extreme-fade strategies,
which fade extreme SHORTS into longs; this fades extreme LONGS into
flat). Sixth COT strategy this cron trigger, sixth market/report type
(first use of the CFTC Disaggregated report's "Managed Money" category,
distinct from Legacy report's "non-commercial"/"leveraged-money" used
earlier this trigger for Bitcoin/Gold/VIX/E-mini-S&P).

**Sources:**
- https://www.google.com/search?q=silver+COT+managed+money+extreme+net+long+contrarian+trading+strategy+specific+rule (browser_exec Google SERP; MetalCharts.org "extreme levels for silver Managed Money positioning... above 60,000 to 70,000")
- https://publicreporting.cftc.gov/resource/72hh-3qpy.json (CFTC Disaggregated Report API, `SILVER - COMMODITY EXCHANGE INC.` market, 1058 weekly rows since 2006-06)

**Data:** SLV/GLD daily OHLCV via `load_equity`; BTC/ETH via `load_crypto` (robustness-check-only).

## Grid test

`param_grid = {lookback_weeks: [104,156,208], high_pct: [0.80,0.85,0.90]}`,
`symbols = {equity: [SLV,GLD], crypto: [BTC/USDT,ETH/USDT]}`.

- total_cells: 108, passed_cells: 9, **pass_fraction: 0.083**
- by_asset_class: equity 9/54 passed (17%, all on GLD not SLV), crypto 0/54 passed
- by_vol_regime: low 9/36, mid 0/36, high 0/36
- best_cell: lookback_weeks=208, high_pct=0.90, GLD, low-vol, Sharpe 3.60
- worst_cell: lookback_weeks=156, high_pct=0.80, BTC/USDT, mid-vol, Sharpe 0.09 (near-zero, not decisively negative — default-long-minus-rare-flat strategy rarely diverges much from buy-and-hold)

Note: bug found and fixed mid-iteration — `_crowded_long_flag`'s boolean
Series had `object` dtype from `.fillna(False)` on a bool-typed Series
constructed via reindex, causing `~crowded` to do bitwise-NOT on ints
instead of logical negation (position values of -1/-2 instead of 0/1).
Fixed with an explicit `.astype(bool)` before negation; grid/validator
numbers below are post-fix.

## Primary-config validation (SLV, lookback_weeks=156, high_pct=0.90 — intended primary asset)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full period) | 1.050 | ≥ 1.0 | PASS |
| Max drawdown | 0.523 | ≤ 0.35 | **FAIL** |
| Transaction cost survival (10bps/trade, 22 trades) | 1.040 net Sharpe | ≥ 0.5 | PASS |
| Walk-forward (4 splits) | 3/4 positive (1.20, -0.33, 1.67, 1.41) = 0.75 | ≥ 0.75 | PASS |
| Parameter sensitivity (9-cell sweep) | relative std 0.096 | ≤ 0.5 | PASS |

## Decision: REJECTED

4 of 5 validators pass, but max drawdown decisively fails (52.3% vs 35%
threshold) — a default-long strategy that only goes flat in rare
top-decile-crowding weeks (only 133 of 1939 days, ~7%, flat) inherits most
of silver's own severe multi-year drawdowns (e.g. the 2011-2015 and 2020
selloffs) since it does not have a general trend/defensive filter, only a
positioning-crowding filter. Strategy file and this report kept as a
record of a rejected attempt; a future loop could retry combining this
crowded-long-avoidance signal with a trend/defensive gate (as Gold's
accepted strategy -038 does) to control drawdown rather than using it as
a standalone default-long overlay.
